# -*- coding: utf-8 -*-
from __future__ import absolute_import

from webchat.mailers.base_mailer import BaseMailer


class PaymentConfirmNotifyMailer(BaseMailer):
    template = 'mailers/payment_confirmation.html'
    from_addr = 'Payment Successful <noreply@apartmentocean.com>'
    subject = u'Payment Notification - Chatbot Portal'

    def send(self, data):
        html = self.render(context=data)

        return self.send_email(
            subject=self.subject,
            text_message=html,
            from_addr=self.from_addr,
            to=[data['email']],
            html_message=html,
            bcc=[
                'support@apartmentocean.com',
            ]
        )
