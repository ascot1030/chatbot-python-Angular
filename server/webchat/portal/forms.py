# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from django import forms
from django.forms import TextInput
from django.forms.utils import ErrorList

from .models import Contact
from .models import Widget

from webchat.mailers.new_contact_notify import NewContactNotifyMailer

logger = logging.getLogger(__name__)


class WidgetUpdateForm(forms.ModelForm):
    class Meta:
        model = Widget
        fields = ["domain", "greeting_message"]
        widgets = {
            'domain': TextInput(attrs={
                'placeholder': 'Enter domain here',
                'class': 'form-control'
            }),
            'greeting_message': TextInput(attrs={
                'placeholder': 'Hi {username}, This is Mary with Apartment Ocean. How are you?',
                'class': 'form-control'
            }),
        }


class FeedBackForm(forms.Form):
    first_name = forms.CharField()
    last_name = forms.CharField()
    email1 = forms.EmailField()
    email2 = forms.EmailField()
    body = forms.CharField()

    def clean(self):
        clean = super(FeedBackForm, self).clean()
        if 'email1' in self.cleaned_data and 'email2' in self.cleaned_data and \
                self.cleaned_data['email1'] != self.cleaned_data['email2']:
            if "email2" not in self._errors:
                errlst = ErrorList()
                self._errors["email2"] = errlst
            else:
                errlst = self._errors["email2"]
            errlst.append(u"The Emails did not match")
        return clean

    def save(self):
        contact = Contact(
            first_name=self.cleaned_data['first_name'],
            last_name=self.cleaned_data['last_name'],
            email=self.cleaned_data['email1'],
            body=self.cleaned_data['body']
        )
        cont = contact.save()

        NewContactNotifyMailer(None).send(self.cleaned_data)
        return cont
