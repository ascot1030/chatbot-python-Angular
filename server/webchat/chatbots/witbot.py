# -*- coding: utf-8 -*-
from __future__ import absolute_import

import json
import logging

from channels import Group
from channels import channel_layers
from django.conf import settings
from wit import Wit

from webchat.portal.models import Room


def send(request, response):
    label = request['session_id']
    room = Room.objects.as_label(label=label)

    content = {
        'nickname': settings.WITAI_BOT_NICKNAME,
        'body': response['text']
    }

    # create and save new message
    m = room.messages.create(**content)
    m.is_support_sender = True
    m.save()
    # put response from Wit.ai to Group
    Group('chat-' + label,
          channel_layer=channel_layers['default']).send({'text': json.dumps(m.as_dict())})

actions = {
    'send': send
}

client = Wit(access_token=settings.WITAI_ACCESS_TOKEN, actions=actions)
client.logger.setLevel(logging.DEBUG)
