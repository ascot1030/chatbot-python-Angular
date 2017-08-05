# -*- coding: utf-8 -*-
from __future__ import absolute_import

import json
import logging

from channels import Group
from channels.auth import channel_session_user
from channels.auth import channel_session_user_from_http
from channels.sessions import channel_session

from webchat.portal.models import Room
from webchat.chatbots.witbot import client

log = logging.getLogger(__name__)


@channel_session_user_from_http
def ws_connect(message):
    # Extract the room from the message. This expects message.path to be of the
    # form /chat/{label}/, and finds a Room if the message path is applicable,
    # and if the Room exists. Otherwise, bails (meaning this is a some othersort
    # of websocket). So, this is effectively a version of _get_object_or_404.
    try:
        prefix, label = message['path'].decode('ascii').strip('/').split('/')
        if prefix != 'chat':
            log.debug('invalid ws path=%s', message['path'])
            return
        room = Room.objects.get(label=label)
    except ValueError:
        log.debug('invalid ws path=%s', message['path'])
        return
    except Room.DoesNotExist:
        log.debug('ws room does not exist label=%s', label)
        return

    log.debug(message['headers'])
    log.debug(message.user)
    log.debug('chat connect room=%s client=%s:%s', room.label, *message['client'])

    # Need to be explicit about the channel layer so that testability works
    # This may be a FIXME?
    Group('chat-' + label,
          channel_layer=message.channel_layer).add(message.reply_channel)

    message.channel_session['room'] = room.label


@channel_session_user
def ws_receive(message):
    # Look up the room from the channel session, bailing if it doesn't exist
    try:
        label = message.channel_session['room']
        room = Room.objects.get(label=label)
    except KeyError:
        log.debug('no room in channel_session')
        return
    except Room.DoesNotExist:
        log.debug('recieved message, buy room does not exist label=%s', label)
        return

    # Parse out a chat message from the content text, bailing if it doesn't
    # conform to the expected message format.
    try:
        data = json.loads(message['text'])
    except ValueError:
        log.debug("ws message isn't json text=%s", message['text'])
        return

    if set(data.keys()) != set(('nickname', 'body')):
        log.debug("ws message unexpected format data=%s", data)
        return

    if data:
        log.debug('chat message room=%s nickname=%s body=%s',
                  room.label, data['nickname'], data['body'])
        log.debug(message.user)
        m = room.messages.create(**data)
        if message.user.is_authenticated() and data['nickname'] != 'You':  # is hack
            m.sender = message.user
            m.is_support_sender = True
            m.save()

        # See above for the note about Group
        Group('chat-' + label,
              channel_layer=message.channel_layer).send({'text': json.dumps(m.as_dict())})

        # Send the text received from the user to Wit.ai
        if room.is_bot_use:
            client.run_actions(label, data['body'], {})


@channel_session
def ws_disconnect(message):
    try:
        label = message.channel_session['room']
        room = Room.objects.get(label=label)
        Group('chat-' + label,
              channel_layer=message.channel_layer).discard(message.reply_channel)
    except (KeyError, Room.DoesNotExist):
        return
    log.debug('disconnect client from chat room=%s', room.label)
