# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from django.conf.urls import url

from . import views

urlpatterns = [
    url(regex=r'^card/$', view=views.ChangeCardView.as_view(), name='update_card'),
    url(regex=r'^make-payment/$', view=views.make_payment, name='make_payment'),
    url(regex=r'^make-payment-api/$', view=views.make_payment_api, name='make_payment_api'),
    url(regex=r'^make-quick-payment/$', view=views.AddCardAndPayView.as_view(), name='make_quick_payment'),

    url(regex=r'^coupon/$', view=views.check_coupon_api, name='check_coupon'),
]
