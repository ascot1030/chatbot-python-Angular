# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import random
import string

import jsonfield
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.core.validators import MaxValueValidator

from webchat.portal.models import Widget

PAYMENT_STATUS = (
    ('1', 'Failed'),
    ('2', 'Success'),
    ('3', 'Pending'),
)


class UserPayment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL)
    widget = models.ForeignKey(Widget, related_name='users_widget')
    amount = models.DecimalField(max_digits=20, decimal_places=1, default=Decimal('0.00'))
    trx_id = models.CharField(max_length=255, blank=True, null=True)
    description = models.CharField(max_length=255, blank=True, null=True)
    bank_account = models.CharField(max_length=255, blank=True, null=True)
    recipient_id = models.CharField(max_length=255, blank=True, null=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    transferred = models.BooleanField(default=False)
    status = models.CharField(max_length=1, choices=PAYMENT_STATUS, default='1')
    history = jsonfield.JSONField(
        default={},
        verbose_name=_("Response"),
        help_text=_("JSON containing response Card from stripe")
    )
    created_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Payment')
        verbose_name_plural = _('Payments')

    def __unicode__(self):
        return "%s's payment" % self.user


class PlanPrice(models.Model):
    name = models.CharField(max_length=255)
    slug = models.CharField(max_length=100)
    price = models.IntegerField()

    def __unicode__(self):
        return str(self.name)


class Coupon(models.Model):
    number = models.CharField(max_length=6, unique=True, blank=True, null=True,
                              help_text='Coupon number will be generated after saving data')
    duration = models.IntegerField(blank=True, null=True,
                                   help_text='In days. Leave blank if its a one-time deal')
    discount = models.PositiveIntegerField(validators=[MaxValueValidator(100), ])
    expired = models.BooleanField(default=False)
    activated_at = models.DateTimeField(blank=True, null=True)
    activated_by = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True)

    @staticmethod
    def coupon_generator(size=6, chars=string.ascii_uppercase + string.digits):
        return ''.join(random.choice(chars) for _ in range(size))

    def save(self, *args, **kwargs):
        if not self.number:
            self.number = self.coupon_generator()
            while Coupon.objects.filter(number=self.number).exists():
                self.number = self.coupon_generator()
        super(Coupon, self).save()

    def __unicode__(self):
        return str(self.number)
