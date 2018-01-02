from django.test import TestCase

from ..models import CyberSourceReply, PaymentToken
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
