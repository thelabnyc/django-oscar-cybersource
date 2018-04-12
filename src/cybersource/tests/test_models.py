from django.test import TestCase

from ..models import CyberSourceReply, PaymentToken, SecureAcceptanceProfile
from .factories import build_accepted_token_reply_data


class PaymentTokenTest(TestCase):
    def test_log_data_parsing(self):
        data = build_accepted_token_reply_data('S123456789')
        log = CyberSourceReply.objects.create(data=data)
        token = PaymentToken.objects.create(
            log=log,
            token=data['payment_token'],
            masked_card_number=data['req_card_number'],
            card_type=data['req_card_type'])

        self.assertEqual(token.card_type_name, 'Visa')
        self.assertEqual(token.billing_zip_code, '10001')
        self.assertEqual(token.expiry_month, '12')
        self.assertEqual(token.expiry_year, '2020')
        self.assertEqual(token.card_last4, '1111')
        self.assertEqual(token.card_holder, 'Bob Smith')


class SecureAcceptanceProfileTest(TestCase):
    def setUp(self):
        SecureAcceptanceProfile.objects.create(
            hostname='foo.example.com',
            profile_id='a',
            access_key='',
            secret_key='',
            is_default=False)
        SecureAcceptanceProfile.objects.create(
            hostname='bar.example.com',
            profile_id='b',
            access_key='',
            secret_key='',
            is_default=False)
        SecureAcceptanceProfile.objects.create(
            hostname='www.example.com',
            profile_id='c',
            access_key='',
            secret_key='',
            is_default=True)


    def test_get_profile(self):
        profile = SecureAcceptanceProfile.get_profile('foo.example.com')
        self.assertEqual(profile.profile_id, 'a')

        profile = SecureAcceptanceProfile.get_profile('bar.example.com')
        self.assertEqual(profile.profile_id, 'b')

        profile = SecureAcceptanceProfile.get_profile('www.example.com')
        self.assertEqual(profile.profile_id, 'c')


    def test_default_fallback(self):
        profile = SecureAcceptanceProfile.get_profile('baz.example.com')
        self.assertEqual(profile.profile_id, 'c')


    def test_no_profiles(self):
        SecureAcceptanceProfile.objects.all().delete()
        profile = SecureAcceptanceProfile.get_profile('www.example.com')
        self.assertEqual(profile.profile_id, '2A37F989-C8B2-4FEF-ACCF-2562577780E2')
