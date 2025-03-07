from datetime import datetime
from random import randrange
import uuid

from ..models import SecureAcceptanceProfile
from ..signature import SecureAcceptanceSigner
from ..utils import encrypt_session_id


def get_sa_profile():
    return SecureAcceptanceProfile.get_profile("testserver")


def build_accepted_token_reply_data(order_number, session_id):
    data = {
        "decision": "ACCEPT",
        "payment_token": "4600379961546299901519",
        "reason_code": "100",
        "req_access_key": "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
        "req_amount": "99.99",
        "req_bill_to_address_city": "Manhattan",
        "req_bill_to_address_country": "US",
        "req_bill_to_address_line1": "627 W 27th st",
        "req_bill_to_address_postal_code": "10001",
        "req_bill_to_address_state": "NY",
        "req_bill_to_email": "foo@example.com",
        "req_bill_to_forename": "Bob",
        "req_bill_to_phone": "18006927753",
        "req_bill_to_surname": "Smith",
        "req_card_expiry_date": "12-2020",
        "req_card_number": "xxxxxxxxxxxx1111",
        "req_card_type": "001",
        "req_currency": "USD",
        "req_customer_ip_address": "8.8.8.8",
        "req_device_fingerprint_id": str(uuid.uuid4()),
        "req_item_0_name": "My Product",
        "req_item_0_quantity": "1",
        "req_item_0_sku": "123456789",
        "req_item_0_unit_price": "99.99",
        "req_line_item_count": "1",
        "req_locale": "en",
        "req_payment_method": "card",
        "req_profile_id": str(uuid.uuid4()),
        "req_reference_number": order_number,
        "req_ship_to_address_city": "Manhattan",
        "req_ship_to_address_country": "US",
        "req_ship_to_address_line1": "627 W 27th st",
        "req_ship_to_address_postal_code": "10001",
        "req_ship_to_address_state": "NY",
        "req_ship_to_forename": "Bob",
        "req_ship_to_phone": "18006927753",
        "req_ship_to_surname": "Smith",
        "req_transaction_type": "create_payment_token",
        "req_transaction_uuid": str(randrange(100000000000, 999999999999)),
        "req_merchant_secure_data4": encrypt_session_id(session_id),
        "request_token": "Ahj/7wSR8sYxolZgxwyeIkG7lw3ZNnDmLNjMqcSPOS4lfDoTAFLiV8OhM0glqN4vpQyaSZbpAd0+3AnI+WMY0SswY4ZPAAAALRaM",
        "transaction_id": str(randrange(0, 99999999999999999999)),
        "utf8": "✓",
    }
    return data


def build_accepted_auth_reply_data(order_number, session_id):
    data = {
        "auth_amount": "99.99",
        "auth_avs_code": "X",
        "auth_avs_code_raw": "I1",
        "auth_code": "888888",
        "auth_response": "100",
        "auth_time": "2016-04-07T140637Z",
        "auth_trans_ref_no": "79872689EMF2SDGN",
        "decision": "ACCEPT",
        "decision_case_priority": "3",
        "decision_early_rcode": "1",
        "decision_early_reason_code": "100",
        "decision_early_return_code": "9999999",
        "decision_rcode": "1",
        "decision_reason_code": "100",
        "decision_return_code": "1320000",
        "decision_rflag": "SOK",
        "decision_rmsg": "Service processed successfully",
        "message": "Request was processed successfully.",
        "req_payment_token": "4600379961546299901519",
        "reason_code": "100",
        "req_access_key": "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
        "req_amount": "99.99",
        "req_bill_to_address_city": "Manhattan",
        "req_bill_to_address_country": "US",
        "req_bill_to_address_line1": "627 W 27th st",
        "req_bill_to_address_postal_code": "10001",
        "req_bill_to_address_state": "NY",
        "req_bill_to_email": "foo@example.com",
        "req_bill_to_forename": "Bob",
        "req_bill_to_phone": "18006927753",
        "req_bill_to_surname": "Smith",
        "req_card_expiry_date": "12-2020",
        "req_card_number": "xxxxxxxxxxxx1111",
        "req_card_type": "001",
        "req_currency": "USD",
        "req_customer_ip_address": "8.8.8.8",
        "req_device_fingerprint_id": str(uuid.uuid4()),
        "req_item_0_name": "My Product",
        "req_item_0_quantity": "1",
        "req_item_0_sku": "123456789",
        "req_item_0_unit_price": "99.99",
        "req_line_item_count": "1",
        "req_locale": "en",
        "req_payment_method": "card",
        "req_profile_id": str(uuid.uuid4()),
        "req_reference_number": order_number,
        "req_ship_to_address_city": "Manhattan",
        "req_ship_to_address_country": "US",
        "req_ship_to_address_line1": "627 W 27th st",
        "req_ship_to_address_postal_code": "10001",
        "req_ship_to_address_state": "NY",
        "req_ship_to_forename": "Bob",
        "req_ship_to_phone": "18006927753",
        "req_ship_to_surname": "Smith",
        "req_transaction_type": "authorization",
        "req_transaction_uuid": str(randrange(100000000000, 999999999999)),
        "req_merchant_secure_data4": encrypt_session_id(session_id),
        "request_token": "Ahj/7wSR8sYxolZgxwyeIkG7lw3ZNnDmLNjMqcSPOS4lfDoTAFLiV8OhM0glqN4vpQyaSZbpAd0+3AnI+WMY0SswY4ZPAAAALRaM",
        "score_bin_country": "US",
        "score_card_issuer": "JPMORGAN CHASE BANK, N.A.",
        "score_card_scheme": "VISA CREDIT",
        "score_host_severity": "1",
        "score_internet_info": "FREE-EM^MM-IPBC",
        "score_ip_city": "new york",
        "score_ip_country": "us",
        "score_ip_routing_method": "fixed",
        "score_ip_state": "ny",
        "score_model_used": "default",
        "score_rcode": "1",
        "score_reason_code": "100",
        "score_return_code": "1070000",
        "score_rflag": "SOK",
        "score_rmsg": "score service was successful",
        "score_score_result": "0",
        "score_time_local": "10:06:36",
        "transaction_id": str(randrange(0, 99999999999999999999)),
        "utf8": "✓",
    }
    return data


def build_review_token_reply_data(order_number, session_id):
    data = {
        "decision": "REVIEW",
        "message": "Decision is REVIEW.",
        "reason_code": "480",
        "req_access_key": "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
        "req_amount": "99.99",
        "req_bill_to_address_city": "Manhattan",
        "req_bill_to_address_country": "US",
        "req_bill_to_address_line1": "627 W 27th st",
        "req_bill_to_address_line2": "",
        "req_bill_to_address_postal_code": "10001",
        "req_bill_to_address_state": "NY",
        "req_bill_to_email": "foo@example.com",
        "req_bill_to_forename": "Bob",
        "req_bill_to_phone": "18006927753",
        "req_bill_to_surname": "Smith",
        "req_card_expiry_date": "12-2020",
        "req_card_number": "xxxxxxxxxxxx1111",
        "req_card_type": "001",
        "req_currency": "USD",
        "req_customer_ip_address": "8.8.8.8",
        "req_device_fingerprint_id": str(uuid.uuid4()),
        "req_item_0_name": "My Product",
        "req_item_0_quantity": "1",
        "req_item_0_sku": "12345678",
        "req_item_0_unit_price": "99.99",
        "req_line_item_count": "1",
        "req_locale": "en",
        "req_payment_method": "card",
        "req_profile_id": str(uuid.uuid4()),
        "req_reference_number": order_number,
        "req_ship_to_address_city": "Manhattan",
        "req_ship_to_address_country": "US",
        "req_ship_to_address_line1": "627 W 27th st",
        "req_ship_to_address_line2": "",
        "req_ship_to_address_postal_code": "10001",
        "req_ship_to_address_state": "NY",
        "req_ship_to_forename": "Bob",
        "req_ship_to_phone": "18006927753",
        "req_ship_to_surname": "Smith",
        "req_transaction_type": "create_payment_token",
        "req_transaction_uuid": str(randrange(100000000000, 999999999999)),
        "request_token": "Ahj77wSR8sY0PySenECSIpcaMXXZAClxoxddkaQR1G8vpJl6SZbpAd0+2AnI+WMaH5JPTiBJAAAA9hKE",
        "req_merchant_secure_data4": encrypt_session_id(session_id),
        "transaction_id": str(randrange(0, 99999999999999999999)),
        "utf8": "✓",
    }
    return data


def build_declined_token_reply_data(order_number, session_id):
    data = {
        "decision": "DECLINE",
        "message": "We encountered a Paymentech problem: Reason: Processor Decline.",
        "reason_code": "203",
        "req_access_key": "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
        "req_amount": "99.99",
        "req_bill_to_address_city": "Manhattan",
        "req_bill_to_address_country": "US",
        "req_bill_to_address_line1": "627 W 27th st",
        "req_bill_to_address_line2": "",
        "req_bill_to_address_postal_code": "10001",
        "req_bill_to_address_state": "NY",
        "req_bill_to_email": "foo@example.com",
        "req_bill_to_forename": "Bob",
        "req_bill_to_phone": "18006927753",
        "req_bill_to_surname": "Smith",
        "req_card_expiry_date": "12-2020",
        "req_card_number": "xxxxxxxxxxxx1111",
        "req_card_type": "001",
        "req_currency": "USD",
        "req_customer_ip_address": "8.8.8.8",
        "req_device_fingerprint_id": str(uuid.uuid4()),
        "req_item_0_name": "My Product",
        "req_item_0_quantity": "1",
        "req_item_0_sku": "12345678",
        "req_item_0_unit_price": "99.99",
        "req_line_item_count": "1",
        "req_locale": "en",
        "req_payment_method": "card",
        "req_profile_id": str(uuid.uuid4()),
        "req_reference_number": order_number,
        "req_ship_to_address_city": "Manhattan",
        "req_ship_to_address_country": "US",
        "req_ship_to_address_line1": "627 W 27th st",
        "req_ship_to_address_line2": "",
        "req_ship_to_address_postal_code": "10001",
        "req_ship_to_address_state": "NY",
        "req_ship_to_forename": "Bob",
        "req_ship_to_phone": "18006927753",
        "req_ship_to_surname": "Smith",
        "req_transaction_type": "create_payment_token",
        "req_transaction_uuid": str(randrange(100000000000, 999999999999)),
        "request_token": "Ahj77wSR8sY0PySenECSIpcaMXXZAClxoxddkaQR1G8vpJl6SZbpAd0+2AnI+WMaH5JPTiBJAAAA9hKE",
        "req_merchant_secure_data4": encrypt_session_id(session_id),
        "transaction_id": str(randrange(0, 99999999999999999999)),
        "utf8": "✓",
    }
    return data


def build_declined_auth_reply_data(order_number, session_id):
    data = {
        "auth_avs_code": "X",
        "auth_avs_code_raw": "I1",
        "auth_response": "303",
        "decision": "DECLINE",
        "decision_early_rcode": "1",
        "decision_early_reason_code": "100",
        "decision_early_return_code": "9999999",
        "message": "We encountered a Paymentech problem: Reason: Processor Decline.",
        "reason_code": "203",
        "req_access_key": "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
        "req_amount": "99.99",
        "req_bill_to_address_city": "Manhattan",
        "req_bill_to_address_country": "US",
        "req_bill_to_address_line1": "627 W 27th st",
        "req_bill_to_address_line2": "",
        "req_bill_to_address_postal_code": "10001",
        "req_bill_to_address_state": "NY",
        "req_bill_to_email": "foo@example.com",
        "req_bill_to_forename": "Bob",
        "req_bill_to_phone": "18006927753",
        "req_bill_to_surname": "Smith",
        "req_card_expiry_date": "12-2020",
        "req_card_number": "xxxxxxxxxxxx1111",
        "req_card_type": "001",
        "req_currency": "USD",
        "req_customer_ip_address": "8.8.8.8",
        "req_device_fingerprint_id": str(uuid.uuid4()),
        "req_item_0_name": "My Product",
        "req_item_0_quantity": "1",
        "req_item_0_sku": "12345678",
        "req_item_0_unit_price": "99.99",
        "req_line_item_count": "1",
        "req_locale": "en",
        "req_payment_method": "card",
        "req_profile_id": str(uuid.uuid4()),
        "req_reference_number": order_number,
        "req_ship_to_address_city": "Manhattan",
        "req_ship_to_address_country": "US",
        "req_ship_to_address_line1": "627 W 27th st",
        "req_ship_to_address_line2": "",
        "req_ship_to_address_postal_code": "10001",
        "req_ship_to_address_state": "NY",
        "req_ship_to_forename": "Bob",
        "req_ship_to_phone": "18006927753",
        "req_ship_to_surname": "Smith",
        "req_transaction_type": "authorization",
        "req_transaction_uuid": str(randrange(100000000000, 999999999999)),
        "request_token": "Ahj77wSR8sY0PySenECSIpcaMXXZAClxoxddkaQR1G8vpJl6SZbpAd0+2AnI+WMaH5JPTiBJAAAA9hKE",
        "req_merchant_secure_data4": encrypt_session_id(session_id),
        "transaction_id": str(randrange(0, 99999999999999999999)),
        "utf8": "✓",
    }
    return data


def build_dmreview_auth_reply_data(order_number, session_id):
    data = {
        "auth_amount": "99.99",
        "auth_avs_code": "X",
        "auth_avs_code_raw": "I1",
        "auth_code": "888888",
        "auth_response": "480",
        "auth_time": "2016-04-07T140637Z",
        "auth_trans_ref_no": "79872689EMF2SDGN",
        "decision": "REVIEW",
        "decision_case_priority": "3",
        "decision_early_rcode": "1",
        "decision_early_reason_code": "100",
        "decision_early_return_code": "9999999",
        "decision_rcode": "0",
        "decision_reason_code": "480",
        "decision_return_code": "1322001",
        "decision_rflag": "DREVIEW",
        "decision_rmsg": "Decision is REVIEW.",
        "message": "Decision is REVIEW.",
        "req_payment_token": "4600379961546299901519",
        "reason_code": "480",
        "req_access_key": "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
        "req_amount": "99.99",
        "req_bill_to_address_city": "Manhattan",
        "req_bill_to_address_country": "US",
        "req_bill_to_address_line1": "627 W 27th st",
        "req_bill_to_address_postal_code": "10001",
        "req_bill_to_address_state": "NY",
        "req_bill_to_email": "foo@example.com",
        "req_bill_to_forename": "Bob",
        "req_bill_to_phone": "18006927753",
        "req_bill_to_surname": "Smith",
        "req_card_expiry_date": "12-2020",
        "req_card_number": "xxxxxxxxxxxx1111",
        "req_card_type": "001",
        "req_currency": "USD",
        "req_customer_ip_address": "8.8.8.8",
        "req_device_fingerprint_id": str(uuid.uuid4()),
        "req_item_0_name": "My Product",
        "req_item_0_quantity": "1",
        "req_item_0_sku": "123456789",
        "req_item_0_unit_price": "99.99",
        "req_line_item_count": "1",
        "req_locale": "en",
        "req_payment_method": "card",
        "req_profile_id": str(uuid.uuid4()),
        "req_reference_number": order_number,
        "req_ship_to_address_city": "Manhattan",
        "req_ship_to_address_country": "US",
        "req_ship_to_address_line1": "627 W 27th st",
        "req_ship_to_address_postal_code": "10001",
        "req_ship_to_address_state": "NY",
        "req_ship_to_forename": "Bob",
        "req_ship_to_phone": "18006927753",
        "req_ship_to_surname": "Smith",
        "req_transaction_type": "authorization",
        "req_transaction_uuid": str(randrange(100000000000, 999999999999)),
        "request_token": "Ahj/7wSR8sYxolZgxwyeIkG7lw3ZNnDmLNjMqcSPOS4lfDoTAFLiV8OhM0glqN4vpQyaSZbpAd0+3AnI+WMY0SswY4ZPAAAALRaM",
        "req_merchant_secure_data4": encrypt_session_id(session_id),
        "score_bin_country": "US",
        "score_card_issuer": "JPMORGAN CHASE BANK, N.A.",
        "score_card_scheme": "VISA CREDIT",
        "score_host_severity": "1",
        "score_internet_info": "FREE-EM^MM-IPBC",
        "score_ip_city": "new york",
        "score_ip_country": "us",
        "score_ip_routing_method": "fixed",
        "score_ip_state": "ny",
        "score_model_used": "default",
        "score_rcode": "1",
        "score_reason_code": "480",
        "score_return_code": "1070000",
        "score_rflag": "SOK",
        "score_rmsg": "score service was successful",
        "score_score_result": "0",
        "score_time_local": "10:06:36",
        "transaction_id": str(randrange(0, 99999999999999999999)),
        "utf8": "✓",
    }
    return data


def sign_reply_data(data):
    profile = get_sa_profile()
    fields = list(data.keys())
    data["signature"] = (
        SecureAcceptanceSigner(profile.secret_key).sign(data, fields).decode("utf8")
    )
    data["signed_date_time"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    data["signed_field_names"] = ",".join(fields)
    return data
