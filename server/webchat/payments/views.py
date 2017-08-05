# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime
import json
import stripe

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.sites.models import Site
from django.forms.utils import ErrorList
from django.http import HttpResponse
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.shortcuts import render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.generic import FormView

from .models import UserPayment
from .models import PlanPrice
from .models import Coupon
from webchat.portal.models import Widget
from webchat.users.models import TRIAL_PERIOD
from .forms import CreditCardForm
from webchat.portal.views import generate_token
from webchat.mailers.payment_confirm_notify import PaymentConfirmNotifyMailer

stripe.api_key = settings.STRIPE_API_KEY


def get_price(plan_name):
    return int(PlanPrice.objects.get(slug=plan_name).price)


class ChangeCardView(FormView):
    template_name = 'payments/add_card.html'
    success_url = '/make-payment/'
    form_class = CreditCardForm

    def form_valid(self, form):
        try:
            token = stripe.Token.create(card={
                "number": form.cleaned_data['number'],
                "exp_month": form.cleaned_data["expiration"].month,
                "exp_year": form.cleaned_data["expiration"].year,
                "cvc": form.cleaned_data['cvc'],
                'name': form.cleaned_data['name'],
            },)
        except Exception as e:
            errors = form._errors.setdefault("number", ErrorList())
            errors.append(e.message)
            return self.form_invalid(form)

        customer = stripe.Customer.create(source=token.id,
                                          description="Payment for {}".format(
                                              self.request.user.username), )

        user = self.request.user
        user.stripe_id = customer['id']
        user.default_card = customer['default_source']
        card = customer['sources']['data'][0]
        user.card_type = card['brand']
        user.card_last = card['last4']
        user.card_expiry = '{}/{}'.format(str(card['exp_month']), str(card['exp_year']))
        user.payment_active = True
        user.save()

        return super(ChangeCardView, self).form_valid(form)

    def get_context_data(self, **kwargs):
        user = self.request.user
        context = super(ChangeCardView, self).get_context_data(**kwargs)
        context['user'] = user
        context['payment_active'] = user.payment_active
        return context

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(ChangeCardView, self).dispatch(*args, **kwargs)


@login_required
def make_payment(request):
    """We can use celery and call this function as a delayed task."""
    user = request.user
    data = dict()
    data['user'] = user
    now = timezone.now()
    standard_price = get_price('standard')

    data['standard_price'] = standard_price
    if Coupon.objects.filter(activated_by=user).exists():
        data['has_coupon'] = True
        coupon = Coupon.objects.get(activated_by=user)
        if not coupon.duration:
            discount = standard_price * Coupon.objects.get(activated_by=user).discount / 100
            data['standard_price'] = standard_price - discount
        else:
            if coupon.activated_at + datetime.timedelta(days=coupon.duration) > now:
                discount = standard_price * Coupon.objects.get(activated_by=user).discount / 100
                data['standard_price'] = standard_price - discount

    if user.paid_at:
        paid_period_expires_at = user.paid_at + datetime.timedelta(days=TRIAL_PERIOD)
        data['paid_period_expires_at'] = paid_period_expires_at
        if paid_period_expires_at < now:
            data['status'] = 200
        else:
            data['status'] = "You still have an existing active plan"
    else:
        if user.payment_active:
            data['status'] = 200
        else:
            data['status'] = 403
            data['invalid_card'] = True

    return render(request, 'payments/make_payment.html', data)


def make_payment_api(request):
    """ todo: move to DRF """
    user = request.user
    amount = get_price('standard')

    if Coupon.objects.filter(activated_by=user).exists():
        coupon = Coupon.objects.get(activated_by=user)
        if not coupon.duration:
            discount = amount * Coupon.objects.get(activated_by=user).discount / 100
            amount -= discount
        else:
            if coupon.activated_at + datetime.timedelta(days=coupon.duration) > timezone.now():
                discount = amount * Coupon.objects.get(activated_by=user).discount / 100
                amount -= discount

    if request.method == 'POST':
        user = request.user

        try:
            widget = Widget.objects.get(owner=request.user)
        except Widget.DoesNotExist:
            token = generate_token()
            widget = Widget.objects.create(owner=request.user, token=token)
        except Widget.MultipleObjectsReturned:
            widget = Widget.objects.filter(owner=request.user)[0]
        try:
            payment = UserPayment.objects.create(
                user=request.user,
                widget=widget,
                amount=amount,
                description="Charge for monthly subscription {}".format(request.user.email)
            )
            charge = stripe.Charge.create(
                amount=int(amount * 100),
                currency="usd",
                customer=user.stripe_id,
                description="Charge for monthly subscription {}".format(request.user.email),
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
            url = "https://{}/users/{}/".format(domain, request.user.username)

            context = {
                'username': request.user.username,
                'email': request.user.email,
                'cost': int(payment.amount),
                'url': url,
                'transaction_id': payment.trx_id
            }
            PaymentConfirmNotifyMailer(request).send(context)

            return HttpResponse(json.dumps({"status": True}), content_type="application/json")
        except Exception as e:
            return HttpResponse(
                json.dumps({"status": False, "msg": str(e)}),
                content_type="application/json"
            )


def check_coupon_api(request):
    """ todo: move to DRF """
    if request.method == 'POST':
        coupon_number = request.POST.get('coupon_number')
        if coupon_number:
            try:
                coupon = Coupon.objects.get(number=coupon_number, expired=False)
                coupon.activated_by = request.user
                coupon.activated_at = timezone.now()
                coupon.expired = True
                coupon.save()
                return HttpResponse(json.dumps({'success': True}), content_type="application/json")
            except Coupon.DoesNotExist:
                return HttpResponse(json.dumps({'success': False}), content_type="application/json")
        else:
            return HttpResponse(json.dumps({'success': False}), content_type="application/json")
    else:
        return HttpResponseForbidden()


class AddCardAndPayView(FormView):
    template_name = 'payments/add_and_pay.html'
    success_url = '/make-payment/?p=quick'
    form_class = CreditCardForm

    def form_valid(self, form):
        try:
            token = stripe.Token.create(card={
                "number": form.cleaned_data['number'],
                "exp_month": form.cleaned_data["expiration"].month,
                "exp_year": form.cleaned_data["expiration"].year,
                "cvc": form.cleaned_data['cvc'],
                'name': form.cleaned_data['name'],
            },)
        except Exception as e:
            errors = form._errors.setdefault("number", ErrorList())
            errors.append(e.message)
            return self.form_invalid(form)

        customer = stripe.Customer.create(source=token.id,
                                          description="Payment for {}".format(
                                              self.request.user.username), )

        user = self.request.user
        user.stripe_id = customer['id']
        user.default_card = customer['default_source']
        card = customer['sources']['data'][0]
        user.card_type = card['brand']
        user.card_last = card['last4']
        user.card_expiry = '{}/{}'.format(str(card['exp_month']), str(card['exp_year']))
        user.payment_active = True
        user.save()

        amount = get_price('standard')

        if Coupon.objects.filter(activated_by=user).exists():
            coupon = Coupon.objects.get(activated_by=user)
            if not coupon.duration:
                discount = amount * Coupon.objects.get(activated_by=user).discount / 100
                amount -= discount
            else:
                if coupon.activated_at + datetime.timedelta(days=coupon.duration) > timezone.now():
                    discount = amount * Coupon.objects.get(activated_by=user).discount / 100
                    amount -= discount

        try:
            widget = Widget.objects.get(owner=user)
        except Widget.DoesNotExist:
            token = generate_token()
            widget = Widget.objects.create(owner=user, token=token)
        except Widget.MultipleObjectsReturned:
            widget = Widget.objects.filter(owner=user)[0]
        try:
            payment = UserPayment.objects.create(
                user=user,
                widget=widget,
                amount=amount,
                description="Charge for monthly subscription {}".format(user.email)
            )
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
            user.is_trial = False
            user.paid_at = timezone.now()
            user.save()

            domain = Site.objects.get_current().domain
            url = "https://{}/users/{}/".format(domain, user.username)

            context = {
                'username': user.username,
                'email': user.email,
                'cost': int(payment.amount),
                'url': url,
                'transaction_id': payment.trx_id
            }
            PaymentConfirmNotifyMailer(None).send(context)
        except Exception, e:
            errors = form._errors.setdefault("number", ErrorList())
            errors.append(e.message)
            return self.form_invalid(form)

        return super(AddCardAndPayView, self).form_valid(form)

    def get_context_data(self, **kwargs):
        user = self.request.user
        context = super(AddCardAndPayView, self).get_context_data(**kwargs)
        context['user'] = user
        context['payment_active'] = user.payment_active
        return context

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(AddCardAndPayView, self).dispatch(*args, **kwargs)
