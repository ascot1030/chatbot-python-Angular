# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from django.conf.urls import url

from . import views

urlpatterns = [
    url(regex=r'^$', view=views.portal, name='home'),
    url(regex=r'^feedback/$', view=views.feedback, name='feedback'),
    url(regex=r'^rooms/$', view=views.rooms, name='rooms'),
    url(regex=r'^statistics/$', view=views.statistics, name='statistics'),
    url(regex=r'^widgets/$', view=views.widgets, name='widgets'),

    url(regex=r'^disable-widget-tip/$', view=views.disable_widget_tip, name='disable_widget_tip'),
]
