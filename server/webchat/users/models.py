# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

import datetime

from django.contrib.auth.models import AbstractUser
from django.core.urlresolvers import reverse
from django.db import models
from django.utils import timezone
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _

from webchat.core.utils import add_months

PLAN_CHOICES = (
    ('0', 'Trial'),
    ('1', 'Standard'),
    ('2', 'Custom'),
)

TRIAL_PERIOD = 30


@python_2_unicode_compatible
class User(AbstractUser):

    # First Name and Last Name do not cover name patterns
    # around the globe.
    location = models.CharField(max_length=50, null=True, blank=True)
    job = models.CharField(max_length=100, null=True, blank=True)
    about_me = models.TextField(null=True, blank=True)
    avatar = models.ImageField(upload_to='portraits/', null=True, blank=True)

    default_card = models.CharField(max_length=255, blank=True, null=True,
                                    verbose_name='Default Card ID')
    card_last = models.CharField(max_length=255, blank=True, null=True)
    card_type = models.CharField(max_length=255, blank=True, null=True)
    stripe_id = models.CharField(max_length=255, blank=True, null=True)
    card_expiry = models.CharField(blank=True, null=True, max_length=255)
    payment_active = models.BooleanField(default=False)
    payment_issue = models.CharField(max_length=255, blank=True, null=True)

    plan = models.CharField(max_length=1, choices=PLAN_CHOICES, default='0')
    is_trial = models.BooleanField(default=True)
    paid_at = models.DateTimeField(blank=True, null=True)

    show_widget_tip = models.BooleanField(default=True)

    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')

    def update_trial(self):
        now = timezone.now()
        if not self.is_trial and self.paid_at:
            paid_period_expires_at = self.paid_at + datetime.timedelta(days=TRIAL_PERIOD)
            if paid_period_expires_at < now:
                self.is_trial = True
                self.save()

    def revoke_access(self):
        now = timezone.now()
        expires_at = self.date_joined + datetime.timedelta(days=TRIAL_PERIOD)
        if expires_at < now:
            return True
        else:
            return False

    def days_left(self):
        days_left = (
            self.date_joined + datetime.timedelta(days=TRIAL_PERIOD) - timezone.now()
        ).days
        return days_left

    def next_pay_day(self):
        if self.paid_at:
            next_pay_day = add_months(self.paid_at, 1)
            return next_pay_day

    def __str__(self):
        return self.username

    def get_absolute_url(self):
        return reverse('users:detail', kwargs={'username': self.username})
