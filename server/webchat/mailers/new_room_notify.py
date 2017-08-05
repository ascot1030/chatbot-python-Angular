# -*- coding: utf-8 -*-
from __future__ import absolute_import

from webchat.mailers.base_mailer import BaseMailer


class NewRoomNotifyMailer(BaseMailer):
    template = 'mailers/new_room_notify.html'
    from_addr = 'Apartment Ocean <support@apartmentocean.com>'
    subject = u'New chat on Apartment Ocean'

    def send(self, data):
        html = self.render({})

        return self.send_email(
            subject=self.subject,
            text_message=html,
            from_addr=self.from_addr,
            to=[data['email']],
            html_message=html
        )
