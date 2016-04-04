from cybersource.models import CyberSourceReply, PaymentToken
from django.test import TestCase


class PaymentTokenTest(TestCase):
    def test_log_data_parsing(self):
        data = {
            "request_token": "Ahj/7wSR7MjuQo1tP0PWIkGLFw0aMmTabKoM68puzT+AhcfwABT+AhcfwDSAC8lDJpJlukB3T7cCcj2ZHchRrafoesAA0g7k",
            "req_payment_method": "card",
            "auth_avs_code": "X",
            "req_currency": "USD",
            "req_transaction_type": "create_payment_token",
            "req_access_key": "103125ca86793c36b69ccbfd93532b9d",
            "auth_amount": "0.00",
            "auth_response": "100",
            "req_reference_number": "fdd6d43c-ca8b-11e5-84fd-0242ac130008",
            "payment_token": "4545138333646166401515",
            "req_bill_to_email": "lfridlikh@thelabnyc.com",
            "utf8": "✓",
            "req_bill_to_forename": "Pop",
            "auth_code": "888888",
            "req_bill_to_phone": "1233211233",
            "decision": "ACCEPT",
            "auth_avs_code_raw": "I1",
            "req_bill_to_address_state": "NY",
            "auth_trans_ref_no": "11844226MJP3WJ73",
            "auth_time": "2016-02-03T153713Z",
            "req_transaction_uuid": "145451383149",
            "transaction_id": "4545138333646166401515",
            "req_bill_to_address_postal_code": "10001",
            "req_bill_to_address_city": "Manhattan",
            "req_card_type": "001",
            "reason_code": "100",
            "signature": "QpPOk0JWCgm83HEuB6Ez2KmRA213QKrR7ILm8nTOG3o=",
            "req_locale": "en",
            "req_bill_to_surname": "Art",
            "req_bill_to_address_country": "US",
            "signed_date_time": "2016-02-03T15:37:13Z",
            "signed_field_names": "transaction_id,decision,req_access_key,req_profile_id,req_transaction_uuid,req_transaction_type,req_reference_number,req_currency,req_locale,req_payment_method,req_bill_to_forename,req_bill_to_surname,req_bill_to_email,req_bill_to_phone,req_bill_to_address_line1,req_bill_to_address_city,req_bill_to_address_state,req_bill_to_address_country,req_bill_to_address_postal_code,req_card_number,req_card_type,req_card_expiry_date,message,reason_code,auth_avs_code,auth_avs_code_raw,auth_response,auth_amount,auth_code,auth_trans_ref_no,auth_time,request_token,payment_token,signed_field_names,signed_date_time",
            "req_profile_id": "465A8696-4412-42D1-A653-D12796182F06",
            "req_card_number": "xxxxxxxxxxxx1111",
            "req_bill_to_address_line1": "637 W 27th St",
            "req_card_expiry_date": "11-2111",
            "message": "Request was processed successfully."
        }
        log = CyberSourceReply.objects.create(data=data)
        token = PaymentToken.objects.create(
            log=log,
            token=data['payment_token'],
            masked_card_number=data['req_card_number'],
            card_type=data['req_card_type'])

        self.assertEquals(token.card_type_name, 'Visa')
        self.assertEquals(token.billing_zip_code, '10001')
        self.assertEquals(token.expiry_month, '11')
        self.assertEquals(token.expiry_year, '2111')
        self.assertEquals(token.card_last4, '1111')
        self.assertEquals(token.card_holder, 'Pop Art')
