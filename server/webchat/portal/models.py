# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _


class WidgetManager(models.Manager):
    """The manager for Widget."""

    def as_token(self, token):
        """Return the widget matching a token."""
        return self.filter(models.Q(token=token))[:1].get()


class Widget(models.Model):
    """A Webchat Widget for installing on a website."""

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True)
    name = models.TextField(null=True, blank=True)
    domain = models.URLField(null=True, blank=True)
    greeting_message = models.TextField(null=True, blank=True)
    token = models.CharField(unique=True, max_length=25)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    is_in_use = models.BooleanField(default=True)

    objects = WidgetManager()

    def __unicode__(self):
        return '{%s} %s' % (
            self.owner,
            self.domain
        )


class RoomManager(models.Manager):
    """The manager for Room."""

    def as_label(self, label):
        """Return the room matching a label."""
        return self.filter(models.Q(label=label))[:1].get()

    def as_owner(self, user, filter):
        """Return rooms matching a filter AND being visible to a user as the owner."""
        return self.filter(
            filter,
            owner=user,
            is_in_use=True
        )

    def as_member(self, user):
        """Return rooms being visible to a user as the member."""
        return self.filter(
            ((models.Q(owner=user) | models.Q(messages__sender=user) |
              models.Q(widget__owner=user)) &
             (models.Q(is_in_use=True)))
        ).distinct()

    def all_active(self):
        """Return all active rooms."""
        return self.filter(is_in_use=True)

    def total_received(self):
        """Return the number of received rooms."""
        return self.filter(is_in_use=True).count()


class Room(models.Model):
    """A private Room for communication between users."""

    widget = models.ForeignKey(Widget, null=True, related_name='incoming_rooms')
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True)
    name = models.TextField(null=True, blank=True)
    label = models.SlugField(unique=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    is_bot_use = models.BooleanField(default=True)
    is_in_use = models.BooleanField(default=True)

    objects = RoomManager()

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Room')
        verbose_name_plural = _('Rooms')

    def __unicode__(self):
        return self.label

    @property
    def formatted_created_at(self):
        return self.created_at.strftime('%b %-d %-I:%M %p')

    def as_dict(self):
        return {'name': self.name, 'label': self.label, 'created_at': self.formatted_created_at}


class MessageManager(models.Manager):
    """The manager for Message."""

    def unread_count(self):
        """Return the number of unread messages for a user."""
        return self.filter(
            read_at__isnull=True,
            room__is_in_use=True
        ).count()

    def sent_count(self, user):
        """Return the number of sent messages for a user."""
        return self.filter(
            sender=user,
            room__is_in_use=True
        ).count()

    def total_received(self):
        """Return the number of received messages from Anonymous."""
        return self.filter(
            sender__isnull=True,
            room__is_in_use=True
        ).count()

    def total_user_received(self, user):
        """Return the number of received messages from Anonymous for user."""
        return self.filter(
            sender__isnull=True,
            room__widget__owner=user,
            room__is_in_use=True
        ).count()

    def as_sender(self, user, filter):
        """Return messages matching a filter AND being visible to a user as the sender."""
        return self.filter(filter, sender=user)

    def set_read(self, user, filter):
        """Set messages as read."""
        return self.filter(
            filter,
            recipient=user,
            read_at__isnull=True,
        ).update(read_at=timezone.now)


class Message(models.Model):
    """A private message between a User and another User or Bot in a Room."""

    room = models.ForeignKey(Room, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                               related_name='sent_messages', verbose_name=_("Sender"))
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                  related_name='received_messages', verbose_name=_("Recipient"))
    nickname = models.TextField(null=True, blank=True)
    body = models.TextField(null=True, blank=True)
    sent_at = models.DateTimeField(_("sent at"), default=timezone.now, db_index=True)
    read_at = models.DateTimeField(_("read at"), null=True, blank=True)
    is_support_sender = models.BooleanField(default=False)

    objects = MessageManager()

    class Meta:
        ordering = ['-sent_at']
        verbose_name = _('Message')
        verbose_name_plural = _('Messages')

    def __unicode__(self):
        return '[{sent_at}] {nickname}: {body}'.format(**self.as_dict())

    @property
    def formatted_sent_at(self):
        return self.sent_at.strftime('%b %-d %-I:%M %p')

    @property
    def formatted_sent_at_time(self):
        return self.sent_at.strftime('%-I:%M %p')

    def as_dict(self):
        return {'nickname': self.nickname, 'body': self.body, 'sent_at': self.formatted_sent_at}

    def is_room_owner(self, user):
        return self.room.owner == user


class Contact(models.Model):
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField()
    body = models.TextField()

    class Meta:
        verbose_name = _('Contact')
        verbose_name_plural = _('Contacts')

    def __unicode__(self):
        return "Message from %s %s" % (self.first_name, self.last_name)
