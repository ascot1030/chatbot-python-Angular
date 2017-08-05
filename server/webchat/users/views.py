# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.views.generic import DetailView
from django.views.generic import TemplateView
from django.views.generic import RedirectView
from django.views.generic import UpdateView

from django.contrib.auth.mixins import LoginRequiredMixin

from webchat.payments.models import UserPayment
from webchat.portal.models import Message
from webchat.portal.models import Room
from .models import User


class UserDetailView(LoginRequiredMixin, DetailView):
    model = User
    # These next two lines tell the view to index lookups by username
    slug_field = 'username'
    slug_url_kwarg = 'username'

    def dispatch(self, request, *args, **kwargs):
        self.username = self.kwargs['username']
        if self.username != request.user.username and not request.user.is_superuser:
            raise PermissionDenied  # HTTP 403
        return super(UserDetailView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(UserDetailView, self).get_context_data(**kwargs)
        context['messages_count'] = Message.objects.sent_count(self.request.user)
        context['rooms_count'] = Room.objects.as_member(self.request.user).count()
        context['payments'] = UserPayment.objects.filter(
            user=self.request.user,
            status='2'
        ).order_by('-created_at')
        return context


class UserRedirectView(LoginRequiredMixin, RedirectView):
    permanent = False

    def get_redirect_url(self):
        return reverse('users:detail',
                       kwargs={'username': self.request.user.username})


class UserUpdateView(LoginRequiredMixin, UpdateView):

    fields = ['name', ]

    # we already imported User in the view code above, remember?
    model = User

    # send the user back to their own page after a successful update
    def get_success_url(self):
        return reverse('users:detail',
                       kwargs={'username': self.request.user.username})

    def get_object(self):
        # Only get the User record for the user making the request
        return User.objects.get(username=self.request.user.username)


class UserListView(LoginRequiredMixin, TemplateView):
    template_name = "users/user_list.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            raise PermissionDenied  # HTTP 403
        return super(UserListView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(UserListView, self).get_context_data(**kwargs)
        context['user_list'] = User.objects.all()
        return context
