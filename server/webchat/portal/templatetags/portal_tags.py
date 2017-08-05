# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import hashlib

from django.template import Library
from django.template.defaultfilters import stringfilter

register = Library()


@register.filter
@stringfilter
def md5(value):
    return hashlib.md5(value).hexdigest()
