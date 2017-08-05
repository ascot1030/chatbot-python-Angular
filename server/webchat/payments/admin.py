# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from django.contrib import admin

from .models import UserPayment
from .models import PlanPrice
from .models import Coupon


class UserPaymentAdmin(admin.ModelAdmin):
    list_display = ['user', 'widget', 'amount', 'status', 'created_at']


class PlanPriceAdmin(admin.ModelAdmin):
    actions = None

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ('name', 'slug')
        return self.readonly_fields

    list_display = ['name', 'price']


class CouponAdmin(admin.ModelAdmin):
    list_display = ['number', 'expired', 'discount']

admin.site.register(UserPayment, UserPaymentAdmin)
admin.site.register(PlanPrice, PlanPriceAdmin)
admin.site.register(Coupon, CouponAdmin)
