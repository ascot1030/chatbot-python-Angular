# -*- coding: utf-8 -*-
from __future__ import absolute_import

import stripe

from celery import task
from datetime import timedelta, datetime
from django.contrib.sites.models import Site
from django.utils import timezone

from webchat.users.models import User
from webchat.payments.models import UserPayment
from webchat.payments.models import Coupon
from webchat.portal.models import Widget

from webchat.portal.views import generate_token
from .views import get_price

from webchat.mailers.payment_confirm_notify import PaymentConfirmNotifyMailer


@task.periodic_task(run_every=timedelta(days=1))
def get_unprocessed_payments():
    return process_payments()


def process_payments():
    all_users = User.objects.filter(payment_active=True, paid_at__isnull=False)
    amount = get_price('standard')
    for user in all_users:
        if user.plan == '1':  # only for Standard Plan
            if Coupon.objects.filter(activated_by=user).exists():
                coupon = Coupon.objects.get(activated_by=user)
                if not coupon.duration:
                    discount = amount * Coupon.objects.get(activated_by=user).discount / 100
                    amount -= discount
                else:
                    if coupon.activated_at + datetime.timedelta(days=coupon.duration) > timezone.now():
                        discount = amount * Coupon.objects.get(activated_by=user).discount / 100
                        amount -= discount
            if timezone.now().date() == user.next_pay_day():
                try:
                    widget = Widget.objects.get(owner=user)
                except Widget.DoesNotExist:
                    token = generate_token()
                    widget = Widget.objects.create(owner=user, token=token)
                except Widget.MultipleObjectsReturned:
                    widget = Widget.objects.filter(owner=user)[0]
                payment = UserPayment.objects.create(
                    user=user,
                    widget=widget,
                    amount=amount,
                    description="Charge for monthly subscription {}".format(user.email)
                )
                try:
                    charge = stripe.Charge.create(
                        amount=int(amount * 100),
                        currency="usd",
                        customer=user.stripe_id,
                        description="Charge for monthly subscription {}".format(user.email),
                    )
                    payment.trx_id = charge.id
                    payment.status = '2'
                    payment.history = charge
                    payment.save()

                    user.plan = '1'
                    user.payment_active = True
                    user.is_trial = False
                    user.paid_at = timezone.now()
                    user.save()

                    domain = Site.objects.get_current().domain
                    url = "https://" + domain + "/users/{}/".format(user.id)

                    context = {
                        'username': user.username,
                        'email': user.email,
                        'cost': int(payment.amount),
                        'url': url,
                        'transaction_id': payment.trx_id
                    }
                    PaymentConfirmNotifyMailer(None).send(context)

                except Exception as e:
                    # assuming that's an error with credit card: removing payment_active flag
                    # todo: log this exception
                    payment.status = '2'
                    payment.history = e
                    payment.save()
                    user.payment_active = False
                    user.is_trial = True
                    user.save()
