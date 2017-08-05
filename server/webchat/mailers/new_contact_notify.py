# -*- coding: utf-8 -*-
from __future__ import absolute_import

from webchat.mailers.base_mailer import BaseMailer


class NewContactNotifyMailer(BaseMailer):
    template = 'mailers/new_contact_notify.html'
    from_addr = 'Apartment Ocean <support@apartmentocean.com>'
    subject = u'New Contact Message Received'

    def send(self, data):
        html = self.render(context=data)

        return self.send_email(
            subject=self.subject,
            text_message=html,
            from_addr=self.from_addr,
            to=[self.from_addr],
            html_message=html
        )
