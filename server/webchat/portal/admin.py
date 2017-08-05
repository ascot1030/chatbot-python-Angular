# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from django.contrib import admin

from .models import Contact
from .models import Message
from .models import Room
from .models import Widget

admin.site.register(Contact)
admin.site.register(Message)
admin.site.register(Room)
admin.site.register(Widget)
