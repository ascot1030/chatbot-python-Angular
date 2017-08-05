# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
import logging
import random
import string

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.db import transaction
from django.http import HttpResponse
from django.http import HttpResponseBadRequest
from django.http import HttpResponseForbidden
from django.http import QueryDict
from django.shortcuts import render
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils import timezone

from haikunator import Haikunator

from .forms import FeedBackForm
from .forms import WidgetUpdateForm
from .models import Message
from .models import Room
from .models import Widget
from webchat.mailers.new_room_notify import NewRoomNotifyMailer

User = get_user_model()
logger = logging.getLogger(__name__)


@login_required
def portal(request):
    if request.user.is_superuser or request.user.is_staff:
        rooms = Room.objects.all_active()
    else:
        rooms = Room.objects.as_member(request.user)
    if rooms.exists():
        messages = reversed(rooms.first().messages.order_by('-sent_at'))
    else:
        messages = None
    try:
        widget = Widget.objects.get(owner=request.user)
    except Widget.DoesNotExist:
        token = generate_token()
        widget = Widget.objects.create(owner=request.user, token=token)
    except Widget.MultipleObjectsReturned:
        widget = Widget.objects.filter(owner=request.user)[0]

    user = request.user
    user.update_trial()
    if user.revoke_access() and request.user.is_trial:
        return redirect('payments:make_payment')

    return render(request, "portal/home.html", {
        'rooms': rooms,
        'messages': messages,
        'widget': widget
    })


@login_required
def statistics(request):
    if request.user.is_superuser or request.user.is_staff:
        total_rooms = Room.objects.total_received()
        total_messages = Message.objects.total_received()
        total_users = User.objects.all().count()
    else:
        total_rooms = Room.objects.as_member(request.user).count()
        total_messages = Message.objects.total_user_received(request.user)
        total_users = 1  # TODO: show count of team members

    return render(request, "portal/statistics.html", {
        'total_rooms': total_rooms,
        'total_messages': total_messages,
        'total_users': total_users
    })


def widgets(request):
    """
    Widget view like REST.
    """
    if request.method == 'GET':
        callback = request.GET.get('callback')
        if callback:
            is_valid = is_valid_token(request)
            data = json.dumps({'is_valid': str(is_valid).lower()})
            return HttpResponse('%s(%s)' % (callback, data), content_type='text/javascript')

        if not request.user.is_authenticated():
            return HttpResponseForbidden()

        try:
            widget = Widget.objects.get(owner=request.user)
        except Widget.DoesNotExist:
            token = generate_token()
            widget = Widget.objects.create(owner=request.user, token=token)
        except Widget.MultipleObjectsReturned:
            widget = Widget.objects.filter(owner=request.user)[0]

        form = WidgetUpdateForm(instance=widget)

        request.user.update_trial()
        if request.user.revoke_access() and request.user.is_trial:
            return redirect('payments:make_payment')

    elif request.method == 'POST':
        widget = Widget.objects.get(owner=request.user)
        form = WidgetUpdateForm(request.POST, instance=widget)
        if form.is_valid():
            form.save()

    return render(request, "widgets/widget_install.html", {
        'widget': widget,
        'form': form,
        'widget_admin_url': settings.WIDGET_ADMIN_URL,
        'widget_root_url': settings.WIDGET_ROOT_URL
    })


def is_valid_token(request):
    token = request.GET.get('token')
    if not token:
        return False
    try:
        widget = Widget.objects.as_token(token)
    except Widget.DoesNotExist:
        return False
    if widget is None:
        return False
    if widget.domain:
        server_name = request.META['HTTP_REFERER']
        domain = server_name.split("//")[-1].split("/")[0]
        logger.debug(request.META)
        if domain not in widget.domain:
            return False
    return True


def generate_token():
    """
    Token generator for Widget.
    """
    alphabet = string.uppercase
    first_letter = ''.join(random.choice(alphabet))
    last_letter = ''.join(random.choice(alphabet))
    digits = ''.join(random.choice(string.digits) for i in range(20))
    digits = insert_dash(digits, 7)
    digits = insert_dash(digits, 11)
    digits = insert_dash(digits, 15)
    token = first_letter + digits + last_letter

    return token


def insert_dash(string, index):
    return string[:index] + '-' + string[index:]


@ensure_csrf_cookie
def rooms(request):
    """
    Room view like REST.
    """
    if request.method == 'GET':
        if not request.user.is_authenticated() and not is_valid_token(request):
            return HttpResponseForbidden()
        # allow JSONP request for widget
        callback = request.GET.get('callback')
        if callback:
            new_room = create_room(request)
            return HttpResponse(
                '%s(%s)' % (callback, json.dumps(new_room.as_dict())),
                content_type='text/javascript'
            )

        if not request.is_ajax():
            return HttpResponseBadRequest()
        if not request.user.is_authenticated():
            return HttpResponseForbidden()
        if 'label' in request.GET:
            label = request.GET.get('label', '')
            room = Room.objects.as_label(label)
            messages = reversed(room.messages.order_by('-sent_at'))
            html = render_to_string('portal/message_chat.html', {
                'request': request,
                'messages': messages
            })
        else:
            if request.user.is_superuser or request.user.is_staff:
                rooms = Room.objects.all_active()
            else:
                rooms = Room.objects.as_member(request.user)
            html = render_to_string('portal/rooms_chat.html', {
                'request': request,
                'rooms': rooms
            })
        return HttpResponse(html)

    elif request.method == 'POST':
        new_room = create_room(request)
        return HttpResponse(json.dumps(new_room.as_dict()), content_type="application/json")

    elif request.method == 'DELETE':
        if not request.user.is_authenticated():
            return HttpResponseForbidden()
        body = QueryDict(request.body)
        label = body['label']
        room = Room.objects.as_label(label)
        room.deleted_at = timezone.now()
        room.is_in_use = False
        room.save()

        return HttpResponse('ok')


def create_room(request):
    new_room = None
    while not new_room:
        with transaction.atomic():
            label = Haikunator().haikunate()

            nickname = request.GET.get('nickname')
            if nickname:
                name = nickname
            else:
                name = Haikunator().haikunate(token_length=0, delimiter=' ')

            if Room.objects.filter(label=label).exists():
                continue
            new_room = Room.objects.create(label=label, name=name)
            if request.user.is_authenticated():
                new_room.owner = request.user
                new_room.save()

            token = request.GET.get('token')
            if token:
                try:
                    widget = Widget.objects.as_token(token)
                except Widget.DoesNotExist:
                    return new_room
                new_room.widget = widget
                new_room.save()
                logger.debug('created room with label=%s from widget_token=%s',
                             new_room.label, widget.token)

                context = {
                    'email': widget.owner.email
                }
                NewRoomNotifyMailer(request).send(context)

    return new_room


def feedback(request):
    if request.method == 'POST':
        context = {}
        feedback_form = FeedBackForm(request.POST)
        context["form"] = feedback_form
        if feedback_form.is_valid():
            feedback_form.save()
            response = redirect('portal:home')
            response['Location'] += '?message_sent=success'
            return response
        else:
            return render(request, 'portal/feedback.html', context)
    else:
        return render(request, 'portal/feedback.html')


def disable_widget_tip(request):
    if request.user.is_authenticated():
        user = request.user
        user.show_widget_tip = False
        user.save()
        return HttpResponse('ok')
    else:
        return HttpResponseForbidden()
