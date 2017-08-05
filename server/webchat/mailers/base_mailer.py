# -*- coding: utf-8 -*-
from __future__ import absolute_import

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string


class BaseMailer:
    template = None

    def __init__(self, request):
        self.request = request

    def render(self, context):
        return render_to_string(self.template, context, self.request)

    def send_email(self, subject, text_message, from_addr, to, html_message, bcc=None,
                   fail_silently=False, files=None):
        if not from_addr:
            from_addr = getattr(settings, 'DEFAULT_FROM_EMAIL')

        if isinstance(to, str):
            if to.find(','):
                to = to.split(',')
        elif not isinstance(to, list):
            to = [to]

        msg = EmailMultiAlternatives(subject, text_message, from_addr, to, bcc=bcc)

        if html_message:
            msg.attach_alternative(html_message, 'text/html')

        if files:
            if not isinstance(files, list):
                files = [files]
            for file in files:
                msg.attach_file(file)

        return msg.send(fail_silently)
