import datetime

import stripe
from django.utils import timezone
from django.test import TestCase

from webchat.portal.models import Widget
from webchat.portal.views import generate_token
from webchat.users.models import User, TRIAL_PERIOD
from .models import UserPayment

STRIPE_API_KEY = 'sk_test_BS2t9JImRsscT1vyWNsPYGLK'


class PaymentsTests(TestCase):
    def setUp(self):
        self.now = timezone.now()
        date_joined = self.now - datetime.timedelta(days=300)
        expired_paid_date = self.now - datetime.timedelta(days=50)
        self.user = User.objects.create(name='test', date_joined=date_joined, paid_at=expired_paid_date,
                                        is_trial=False, email='test@test.com')

    def test_revoke_access(self):
        """ Restrict access to pages if date_joined < now + trial period """
        self.assertIs(self.user.revoke_access(), True)

    def test_update_plan(self):
        """ Test to check if it sets is_trial to True if paid_at is outdated """
        self.user.update_trial()
        self.assertIs(self.user.is_trial, True)

    def test_make_payment(self):
        if self.user.paid_at:
            paid_period_expires_at = self.user.paid_at + datetime.timedelta(days=TRIAL_PERIOD)
            self.assertIsNotNone(paid_period_expires_at)
            if paid_period_expires_at < self.now:
                create_payment = True
            else:
                create_payment = False
        else:
            create_payment = True

        self.assertTrue(create_payment)

    def test_make_payment_api_fail(self):
        """ Current user doesn't have a valid card and stripe_id """
        token = generate_token()
        widget = Widget.objects.create(owner=self.user, token=token)

        UserPayment.objects.create(
            user=self.user,
            widget=widget,
            amount=50,
            description="Charge for monthly subscription {}".format(self.user.email)
        )
        self.assertEqual(UserPayment.objects.count(), 1)

        try:
            stripe.Charge.create(
                amount=int(50 * 100),
                currency="usd",
                customer=self.user.stripe_id,
                description="Charge for monthly subscription {}".format(self.user.email),
            )
        except stripe.InvalidRequestError:
            self.assertRaises(stripe.InvalidRequestError)

    def test_add_card(self):
        """ Adding test card using TEST_API_KEY """
        stripe.api_key = STRIPE_API_KEY
        token = stripe.Token.create(
            card={
                'number': '4242424242424242',
                'exp_month': '6',
                'exp_year': str(datetime.date.today().year + 1),
                'cvc': '123',
            }
        )
        self.assertTrue(token.id)
