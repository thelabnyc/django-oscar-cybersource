from decimal import Decimal as D
from unittest import mock, skipIf, skipUnless
import datetime

from django.urls import reverse
from django.utils.crypto import get_random_string
from oscar.core.loading import get_model
from oscar.test import factories
from rest_framework import status
from rest_framework.test import APITestCase
import requests_mock

from .. import actions
from ..conf import settings
from ..constants import CyberSourceReplyType, Decision
from ..models import CyberSourceReply
from ..test import responses
from . import factories as cs_factories

Basket = get_model("basket", "Basket")
Product = get_model("catalogue", "Product")
Order = get_model("order", "Order")

# Do we have the appropriate settings, via env vars, to perform full SOAP integration tests?
DO_SOAP = settings.MERCHANT_ID and settings.PKCS12_DATA


# Mock cybersource.models.CyberSourceReply.log_soap_response with this
def mock_log_soap_response(order, response, request=None, card_expiry_date=None):
    response = {
        "decision": response.decision,
        "merchantReferenceCode": response.merchantReferenceCode,
    }

    response["req_reference_number"] = response.get("merchantReferenceCode", "")

    log = CyberSourceReply(
        user=request.user if request and request.user.is_authenticated else None,
        order=order,
        reply_type=CyberSourceReplyType.SA,
        data=response,
        auth_avs_code=response.get("auth_avs_code"),
        auth_code=response.get("auth_code"),
        auth_response=response.get("auth_response"),
        auth_trans_ref_no=response.get("auth_trans_ref_no"),
        decision=response.get("decision"),
        message=response.get("message"),
        reason_code=response.get("reason_code"),
        req_bill_to_address_postal_code=response.get("req_bill_to_address_postal_code"),
        req_bill_to_forename=response.get("req_bill_to_forename"),
        req_bill_to_surname=response.get("req_bill_to_surname"),
        req_card_expiry_date=response.get("req_card_expiry_date"),
        req_reference_number=response.get("req_reference_number"),
        req_transaction_type=response.get("req_transaction_type"),
        req_transaction_uuid=response.get("req_transaction_uuid"),
        request_token=response.get("request_token"),
        transaction_id=response.get("transaction_id"),
    )
    log.save()
    return log


class BaseCheckoutTest(APITestCase):
    fixtures = ["cybersource-test.yaml"]

    def create_product(self, price=D("10.00")):
        product = factories.create_product(
            title="My Product", product_class="My Product Class"
        )
        record = factories.create_stockrecord(
            currency="USD", product=product, num_in_stock=10, price=price
        )
        factories.create_purchase_info(record)
        return product

    def do_add_to_basket(self, product_id, quantity=1):
        url = reverse("api-basket-add-product")
        data = {
            "url": reverse("product-detail", args=[product_id]),
            "quantity": quantity,
        }
        return self.client.post(url, data)

    def do_get_basket(self):
        url = reverse("api-basket")
        return self.client.get(url)

    def do_checkout(self, basket_id, extra_data={}):
        data = {
            "guest_email": "joe@example.com",
            "basket": reverse("basket-detail", args=[basket_id]),
            "shipping_address": {
                "first_name": "Joe",
                "last_name": "Schmoe",
                "line1": "234 5th Ave",
                "line4": "Manhattan",
                "postcode": "10001",
                "state": "NY",
                "country": reverse("country-detail", args=["US"]),
                "phone_number": "+1 (717) 467-1111",
            },
            "billing_address": {
                "first_name": "Joe",
                "last_name": "Schmoe",
                "line1": "234 5th Ave",
                "line4": "Manhattan",
                "postcode": "10001",
                "state": "NY",
                "country": reverse("country-detail", args=["US"]),
                "phone_number": "+1 (717) 467-1111",
            },
            "payment": {
                "cybersource": {
                    "enabled": True,
                }
            },
        }
        data.update(extra_data)
        url = reverse("api-checkout")
        return self.client.post(url, data, format="json")

    def do_fetch_payment_states(self):
        return self.client.get(reverse("api-payment"))

    def do_cs_get_token(self, cs_url, fields, extra_fields={}):
        next_year = datetime.date.today().year + 1
        cs_req_data = {
            "card_type": "001",
            "card_number": "4111111111111111",
            "card_cvn": "123",
            "card_expiry_date": "12-{}".format(next_year),
        }
        for field in fields:
            if not field["editable"] or field["key"] not in cs_req_data:
                cs_req_data[field["key"]] = field["value"]
        cs_req_data.update(extra_fields)
        cs_resp_data = self._build_cs_get_token_response(cs_req_data)
        url = reverse("cybersource-reply")
        return self.client.post(url, cs_resp_data)

    def _build_cs_get_token_response(self, token_request_data):
        token_resp_data = {}
        # Pass through req_* properties
        for key, value in token_request_data.items():
            token_resp_data["req_{}".format(key)] = value
        # Mask Card data
        token_resp_data["req_card_number"] = (
            "xxxxxxxxxxxx" + token_resp_data["req_card_number"][-4:]
        )
        token_resp_data.pop("req_card_cvn", None)
        # Add auth fields
        token_resp_data["auth_amount"] = token_request_data.get("amount", "0.00")
        token_resp_data["auth_avs_code"] = "Y"
        token_resp_data["auth_avs_code_raw"] = "Y"
        token_resp_data["auth_code"] = "00000D"
        token_resp_data["auth_cv_result"] = "M"
        token_resp_data["auth_cv_result_raw"] = "M"
        token_resp_data["auth_response"] = "85"
        token_resp_data["auth_time"] = datetime.datetime.utcnow().strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        token_resp_data["decision"] = "ACCEPT"
        token_resp_data["message"] = "Request was processed successfully."
        token_resp_data["payment_token"] = get_random_string(16)
        token_resp_data["reason_code"] = "100"
        token_resp_data["request_token"] = get_random_string(80)
        token_resp_data["transaction_id"] = get_random_string(
            22, allowed_chars="0123456789"
        )
        # Sign and return data
        cs_factories.sign_reply_data(token_resp_data)
        token_resp_data["utf8"] = "✓"
        return token_resp_data

    def check_finished_order(
        self, number, product_id, quantity=1, status=Decision.ACCEPT, card_last4="1111"
    ):
        # Order exists and was paid for
        self.assertEqual(Order.objects.all().count(), 1)
        order = Order.objects.get()
        self.assertEqual(order.number, number)

        lines = order.lines.all()
        self.assertEqual(lines.count(), 1)
        line = lines[0]
        self.assertEqual(line.quantity, quantity)
        self.assertEqual(line.product_id, product_id)

        payment_events = order.payment_events.filter(event_type__name="Authorise")
        self.assertEqual(payment_events.count(), 1)
        self.assertEqual(payment_events[0].amount, D("10.00"))

        payment_sources = order.sources.all()
        self.assertEqual(payment_sources.count(), 1)
        self.assertEqual(payment_sources[0].currency, order.currency)
        self.assertEqual(payment_sources[0].amount_allocated, D("10.00"))
        self.assertEqual(payment_sources[0].amount_debited, D("0.00"))
        self.assertEqual(payment_sources[0].amount_refunded, D("0.00"))

        transactions = payment_sources[0].transactions.all()
        self.assertEqual(transactions.count(), 1)
        self.assertEqual(transactions[0].txn_type, "Authorise")
        self.assertEqual(transactions[0].amount, D("10.00"))
        self.assertEqual(transactions[0].status, status)

        self.assertEqual(transactions[0].log.order, order)
        self.assertEqual(transactions[0].token.card_last4, card_last4)
        self.assertEqual(transactions[0].token.log.order, order)
        self.assertEqual(transactions[0].token.log.req_reference_number, order.number)

        if status == Decision.REVIEW:
            self.assertEqual(order.notes.count(), 1, "Should save OrderNote")
            note = order.notes.first()
            self.assertEqual(note.note_type, "System")
            self.assertEqual(
                note.message,
                "Transaction %s is currently under review. "
                "Use Decision Manager to either accept or "
                "reject the transaction." % transactions[0].reference,
            )

    def capture_payment(self, number, card_last4="1111"):
        order = Order.objects.get(number=number)

        # Check preconditions
        payment_sources = order.sources.all()
        self.assertEqual(payment_sources.count(), 1)
        self.assertEqual(payment_sources[0].currency, order.currency)
        self.assertEqual(payment_sources[0].amount_allocated, order.total_incl_tax)
        self.assertEqual(payment_sources[0].amount_debited, D("0.00"))
        self.assertEqual(payment_sources[0].amount_refunded, D("0.00"))

        # Capture payment
        transactions = payment_sources[0].transactions.all()
        auth_txn = transactions[0]
        capture_txn = actions.CapturePayment(order)(auth_txn, amount=auth_txn.amount)

        # Payment source now has amount debited too
        payment_sources = order.sources.all()
        self.assertEqual(payment_sources.count(), 1)
        self.assertEqual(payment_sources[0].currency, order.currency)
        self.assertEqual(payment_sources[0].amount_allocated, order.total_incl_tax)
        self.assertEqual(payment_sources[0].amount_debited, order.total_incl_tax)
        self.assertEqual(payment_sources[0].amount_refunded, D("0.00"))

        # Check transaction
        self.assertEqual(capture_txn.txn_type, "Debit")
        self.assertEqual(capture_txn.amount, order.total_incl_tax)
        self.assertEqual(capture_txn.status, Decision.ACCEPT)
        self.assertEqual(capture_txn.log.order, order)
        self.assertEqual(capture_txn.log.req_reference_number, "118031289162")
        self.assertEqual(capture_txn.token.card_last4, card_last4)
        self.assertEqual(capture_txn.token.log.order, order)
        self.assertEqual(capture_txn.token.log.req_reference_number, order.number)

        # Attempting to capture again causes a ValueError
        with self.assertRaises(ValueError):
            # Capture payment
            actions.CapturePayment(order)(auth_txn, amount=auth_txn.amount)


class CheckoutIntegrationTest(BaseCheckoutTest):
    """Full Integration Test of Checkout using mocked SOAP integration"""

    @mock.patch("cybersource.models.CyberSourceReply.log_soap_response")
    @requests_mock.mock()
    def test_checkout_process(self, log_soap_response, rmock):
        """Full checkout process using minimal api calls"""
        product = self.create_product()

        resp = self.do_get_basket()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        basket_id = resp.data["id"]

        resp = self.do_add_to_basket(product.id)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        resp = self.do_checkout(basket_id)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        order_number = resp.data["number"]

        resp = self.do_fetch_payment_states()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["order_status"], "Pending")
        self.assertEqual(
            resp.data["payment_method_states"]["cybersource"]["status"], "Pending"
        )
        self.assertEqual(
            resp.data["payment_method_states"]["cybersource"]["amount"], "10.00"
        )
        self.assertEqual(
            resp.data["payment_method_states"]["cybersource"]["required_action"][
                "name"
            ],
            "get-token",
        )

        responses.mock_soap_transaction_response(rmock, responses.SOAP_AUTH_ACCEPT)
        log_soap_response.side_effect = mock_log_soap_response

        action = resp.data["payment_method_states"]["cybersource"]["required_action"]
        resp = self.do_cs_get_token(action["url"], action["fields"])
        self.assertEqual(resp.status_code, status.HTTP_302_FOUND)

        resp = self.do_fetch_payment_states()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["order_status"], "Authorized")
        self.assertEqual(
            resp.data["payment_method_states"]["cybersource"]["status"], "Consumed"
        )
        self.assertEqual(
            resp.data["payment_method_states"]["cybersource"]["amount"], "10.00"
        )
        self.assertIsNone(
            resp.data["payment_method_states"]["cybersource"]["required_action"]
        )

        self.check_finished_order(order_number, product.id)

        # Now capture payment
        rmock.reset_mock()
        responses.mock_soap_transaction_response(rmock, responses.SOAP_CAPTURE)
        self.capture_payment(order_number)

    @mock.patch("oscarapicheckout.signals.order_payment_declined.send")
    @mock.patch("cybersource.models.CyberSourceReply.log_soap_response")
    @requests_mock.mock()
    def test_checkout_process_declined_auth(
        self, log_soap_response, send_order_payment_declined_signal, rmock
    ):
        """Full checkout process using minimal api calls"""
        product = self.create_product()

        self.assertEqual(send_order_payment_declined_signal.call_count, 0)

        resp = self.do_get_basket()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        basket_id = resp.data["id"]

        resp = self.do_add_to_basket(product.id)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        resp = self.do_checkout(basket_id)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        resp = self.do_fetch_payment_states()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["order_status"], "Pending")
        self.assertEqual(
            resp.data["payment_method_states"]["cybersource"]["status"], "Pending"
        )
        self.assertEqual(
            resp.data["payment_method_states"]["cybersource"]["amount"], "10.00"
        )
        self.assertEqual(
            resp.data["payment_method_states"]["cybersource"]["required_action"][
                "name"
            ],
            "get-token",
        )

        responses.mock_soap_transaction_response(rmock, responses.SOAP_AUTH_REJECT)
        log_soap_response.side_effect = mock_log_soap_response

        action = resp.data["payment_method_states"]["cybersource"]["required_action"]
        resp = self.do_cs_get_token(action["url"], action["fields"])
        self.assertEqual(resp.status_code, status.HTTP_302_FOUND)

        resp = self.do_fetch_payment_states()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["order_status"], "Payment Declined")
        self.assertEqual(
            resp.data["payment_method_states"]["cybersource"]["status"], "Declined"
        )
        self.assertEqual(
            resp.data["payment_method_states"]["cybersource"]["amount"], "10.00"
        )
        self.assertIsNone(
            resp.data["payment_method_states"]["cybersource"]["required_action"]
        )

        # Make sure order_payment_declined signal was triggered exactly once
        self.assertEqual(send_order_payment_declined_signal.call_count, 1)

    @mock.patch("cybersource.models.CyberSourceReply.log_soap_response")
    @requests_mock.mock()
    def test_decision_manager_review_auth(self, log_soap_response, rmock):
        product = self.create_product()

        resp = self.do_get_basket()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        basket_id = resp.data["id"]

        resp = self.do_add_to_basket(product.id)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        resp = self.do_checkout(
            basket_id,
            extra_data={
                "shipping_address": {
                    "first_name": "Joe",
                    "last_name": "Review",  # trigger a review, per a custom rule in CyberSource admin
                    "line1": "234 5th Ave",
                    "line4": "Manhattan",
                    "postcode": "10001",
                    "state": "NY",
                    "country": reverse("country-detail", args=["US"]),
                    "phone_number": "+1 (717) 467-1111",
                },
            },
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        order_number = resp.data["number"]

        resp = self.do_fetch_payment_states()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["order_status"], "Pending")
        self.assertEqual(
            resp.data["payment_method_states"]["cybersource"]["status"], "Pending"
        )
        self.assertEqual(
            resp.data["payment_method_states"]["cybersource"]["amount"], "10.00"
        )
        self.assertEqual(
            resp.data["payment_method_states"]["cybersource"]["required_action"][
                "name"
            ],
            "get-token",
        )

        responses.mock_soap_transaction_response(rmock, responses.SOAP_AUTH_REVIEW)
        log_soap_response.side_effect = mock_log_soap_response

        action = resp.data["payment_method_states"]["cybersource"]["required_action"]
        resp = self.do_cs_get_token(action["url"], action["fields"])
        self.assertEqual(resp.status_code, status.HTTP_302_FOUND)

        resp = self.do_fetch_payment_states()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["order_status"], "Authorized")
        self.assertEqual(
            resp.data["payment_method_states"]["cybersource"]["status"], "Consumed"
        )
        self.assertEqual(
            resp.data["payment_method_states"]["cybersource"]["amount"], "10.00"
        )
        self.assertIsNone(
            resp.data["payment_method_states"]["cybersource"]["required_action"]
        )

        self.check_finished_order(order_number, product.id, status="REVIEW")

    @mock.patch("cybersource.models.CyberSourceReply.log_soap_response")
    @requests_mock.mock()
    def test_add_product_during_auth(self, log_soap_response, rmock):
        """Test attempting to add a product during the authorize flow"""
        product = self.create_product()

        resp = self.do_get_basket()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        basket_id = resp.data["id"]

        # Adding a product here should succeed
        resp = self.do_add_to_basket(product.id)
        basket1 = resp.data["id"]
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        resp = self.do_checkout(basket_id)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        order_number = resp.data["number"]

        # Adding a product here should go to a new basket, not the one we're auth'ing
        resp = self.do_add_to_basket(product.id)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        basket2 = resp.data["id"]
        self.assertNotEqual(basket1, basket2)

        # Finish checkout process
        resp = self.do_fetch_payment_states()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["order_status"], "Pending")
        self.assertEqual(
            resp.data["payment_method_states"]["cybersource"]["required_action"][
                "name"
            ],
            "get-token",
        )

        responses.mock_soap_transaction_response(rmock, responses.SOAP_AUTH_ACCEPT)
        log_soap_response.side_effect = mock_log_soap_response

        action = resp.data["payment_method_states"]["cybersource"]["required_action"]
        resp = self.do_cs_get_token(action["url"], action["fields"])
        self.assertEqual(resp.status_code, status.HTTP_302_FOUND)

        resp = self.do_fetch_payment_states()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["order_status"], "Authorized")
        self.check_finished_order(order_number, product.id)

        # Adding a product here should go to basket2, not basket1
        resp = self.do_add_to_basket(product.id)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        basket3 = resp.data["id"]
        self.assertEqual(basket2, basket3)

    def test_pay_for_nothing(self):
        """Test attempting to pay for an empty basket"""
        resp = self.do_get_basket()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        basket_id = resp.data["id"]

        resp = self.do_checkout(basket_id)
        self.assertEqual(resp.status_code, status.HTTP_406_NOT_ACCEPTABLE)

    def test_manipulate_total_pre_auth(self):
        """Test attempting to manipulate basket price when requesting an auth form"""
        product = self.create_product()

        resp = self.do_get_basket()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        basket_id = resp.data["id"]

        resp = self.do_add_to_basket(product.id)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["total_incl_tax"], "10.00")

        resp = self.do_checkout(
            basket_id,
            extra_data={
                "total": "2.00",  # Try and get $10 of product for only $2
            },
        )
        self.assertEqual(resp.status_code, status.HTTP_406_NOT_ACCEPTABLE)

    @mock.patch("cybersource.models.CyberSourceReply.log_soap_response")
    @requests_mock.mock()
    def test_free_product(self, log_soap_response, rmock):
        """Full checkout process using minimal api calls"""
        product = self.create_product(price=D("0.00"))

        resp = self.do_get_basket()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        basket_id = resp.data["id"]

        resp = self.do_add_to_basket(product.id)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        resp = self.do_checkout(basket_id)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        order_number = resp.data["number"]

        resp = self.do_fetch_payment_states()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["order_status"], "Pending")
        self.assertEqual(
            resp.data["payment_method_states"]["cybersource"]["required_action"][
                "name"
            ],
            "get-token",
        )

        responses.mock_soap_transaction_response(rmock, responses.SOAP_AUTH_ACCEPT)
        log_soap_response.side_effect = mock_log_soap_response

        action = resp.data["payment_method_states"]["cybersource"]["required_action"]
        resp = self.do_cs_get_token(action["url"], action["fields"])
        self.assertEqual(resp.status_code, status.HTTP_302_FOUND)

        resp = self.do_fetch_payment_states()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["order_status"], "Authorized")
        self.check_finished_order(order_number, product.id)


class BluefinCheckoutIntegrationTest(BaseCheckoutTest):
    """Full Integration Test of Checkout"""

    @skipUnless(DO_SOAP, "No SOAP keys, skipping integration test.")
    @mock.patch("oscarapicheckout.signals.order_payment_declined.send")
    def test_bluefin_checkout_ok(self, send_order_payment_declined_signal):
        """Full Bluefin checkout process"""
        product = self.create_product()

        self.assertEqual(send_order_payment_declined_signal.call_count, 0)

        resp = self.do_get_basket()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        basket_id = resp.data["id"]

        resp = self.do_add_to_basket(product.id)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        # Use VISA 4111-1111-1111-1111 with a 12/50 expiration date
        resp = self.do_checkout(
            basket_id,
            extra_data={
                "payment": {
                    "bluefin": {
                        "enabled": True,
                        "payment_data": (
                            "02A600C0170018008292;4111********1111=5012?*1773F3F449C0B83318721C1837DA42160EBE"
                            "B56AB3979BE800000000000000000000000000000000000000003834335531313837393262994996"
                            "0E004A80000610D203"
                        ),
                    }
                }
            },
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        order_number = resp.data["number"]

        resp = self.do_fetch_payment_states()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["order_status"], "Authorized")
        self.assertEqual(
            resp.data["payment_method_states"]["bluefin"]["status"], "Consumed"
        )
        self.assertEqual(
            resp.data["payment_method_states"]["bluefin"]["amount"], "10.00"
        )
        self.assertIsNone(
            resp.data["payment_method_states"]["bluefin"]["required_action"]
        )

        # don't expect a card_last4, since we're using encrypted card info
        self.check_finished_order(order_number, product.id)
        self.assertEqual(send_order_payment_declined_signal.call_count, 0)

    @skipUnless(DO_SOAP, "No SOAP keys, skipping integration test.")
    @mock.patch("oscarapicheckout.signals.order_payment_declined.send")
    def test_bluefin_expired(self, send_order_payment_declined_signal):
        """Full Bluefin checkout process with expired card"""
        product = self.create_product()

        self.assertEqual(send_order_payment_declined_signal.call_count, 0)

        resp = self.do_get_basket()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        basket_id = resp.data["id"]

        resp = self.do_add_to_basket(product.id)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        # Use VISA 4111-1111-1111-1111 with a 12/18 expiration date
        resp = self.do_checkout(
            basket_id,
            extra_data={
                "payment": {
                    "bluefin": {
                        "enabled": True,
                        "payment_data": (
                            "02A600C0170018008292;4111********1111=1812?*F34830CD08A5756641F0013117D267339592"
                            "342CE5A3832200000000000000000000000000000000000000003834335531313837393262994996"
                            "0E004A8000071A6803"
                        ),
                    }
                }
            },
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        resp = self.do_fetch_payment_states()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["order_status"], "Payment Declined")
        self.assertEqual(
            resp.data["payment_method_states"]["bluefin"]["status"], "Declined"
        )
        self.assertEqual(
            resp.data["payment_method_states"]["bluefin"]["amount"], "10.00"
        )
        self.assertIsNone(
            resp.data["payment_method_states"]["bluefin"]["required_action"]
        )

        self.assertEqual(send_order_payment_declined_signal.call_count, 1)

    @skipUnless(DO_SOAP, "No SOAP keys, skipping integration test.")
    def test_bluefin_bad_data(self):
        """Full Bluefin checkout process with bad payment data"""
        product = self.create_product()

        resp = self.do_get_basket()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        basket_id = resp.data["id"]

        resp = self.do_add_to_basket(product.id)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        # Use VISA 4111-1111-1111-1111 with a 12/18 expiration date
        resp = self.do_checkout(
            basket_id,
            extra_data={
                "payment": {"bluefin": {"enabled": True, "payment_data": "FOO"}}
            },
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        resp = self.do_fetch_payment_states()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["order_status"], "Payment Declined")
        self.assertEqual(
            resp.data["payment_method_states"]["bluefin"]["status"], "Declined"
        )
        self.assertEqual(
            resp.data["payment_method_states"]["bluefin"]["amount"], "10.00"
        )
        self.assertIsNone(
            resp.data["payment_method_states"]["bluefin"]["required_action"]
        )

    @skipUnless(DO_SOAP, "No SOAP keys, skipping integration test.")
    def test_bluefin_decline(self):
        """Full Bluefin checkout process with decline"""
        product = self.create_product()

        resp = self.do_get_basket()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        basket_id = resp.data["id"]

        resp = self.do_add_to_basket(product.id)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        # Use VISA 4111-1111-1111-1111 with a 12/50 expiration date
        resp = self.do_checkout(
            basket_id,
            extra_data={
                "payment": {
                    "bluefin": {
                        "enabled": True,
                        "payment_data": (
                            "02A600C0170018008292;4111********1111=5012?*1773F3F449C0B83318721C1837DA42160EBE"
                            "B56AB3979BE800000000000000000000000000000000000000003834335531313837393262994996"
                            "0E004A80000610D203"
                        ),
                    }
                },
                "shipping_address": {
                    "first_name": "Joe",
                    "last_name": "Reject",  # trigger a decline, per a custom rule in CyberSource admin
                    "line1": "234 5th Ave",
                    "line4": "Manhattan",
                    "postcode": "10001",
                    "state": "NY",
                    "country": reverse("country-detail", args=["US"]),
                    "phone_number": "+1 (717) 467-1111",
                },
            },
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        resp = self.do_fetch_payment_states()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["order_status"], "Payment Declined")
        self.assertEqual(
            resp.data["payment_method_states"]["bluefin"]["status"], "Declined"
        )
        self.assertEqual(
            resp.data["payment_method_states"]["bluefin"]["amount"], "10.00"
        )
        self.assertIsNone(
            resp.data["payment_method_states"]["bluefin"]["required_action"]
        )

    # @skipUnless(DO_SOAP, "No SOAP keys, skipping integration test.")
    @skipIf(True, "TODO: Why we're getting REVIEW status on the GetPaymentToken call")
    def test_bluefin_decision_manager_review_auth(self):
        """Full Bluefin checkout process with review"""
        product = self.create_product()

        resp = self.do_get_basket()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        basket_id = resp.data["id"]

        resp = self.do_add_to_basket(product.id)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        # Use VISA 4111-1111-1111-1111 with a 12/50 expiration date
        resp = self.do_checkout(
            basket_id,
            extra_data={
                "payment": {
                    "bluefin": {
                        "enabled": True,
                        "payment_data": (
                            "02A600C0170018008292;4111********1111=5012?*1773F3F449C0B83318721C1837DA42160EBE"
                            "B56AB3979BE800000000000000000000000000000000000000003834335531313837393262994996"
                            "0E004A80000610D203"
                        ),
                    }
                },
                "shipping_address": {
                    "first_name": "Joe",
                    "last_name": "Review",  # trigger a review, per a custom rule in CyberSource admin
                    "line1": "234 5th Ave",
                    "line4": "Manhattan",
                    "postcode": "10001",
                    "state": "NY",
                    "country": reverse("country-detail", args=["US"]),
                    "phone_number": "+1 (717) 467-1111",
                },
            },
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        order_number = resp.data["number"]

        resp = self.do_fetch_payment_states()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["order_status"], "Authorized")
        self.assertEqual(
            resp.data["payment_method_states"]["bluefin"]["status"], "Consumed"
        )
        self.assertEqual(
            resp.data["payment_method_states"]["bluefin"]["amount"], "10.00"
        )
        self.assertIsNone(
            resp.data["payment_method_states"]["bluefin"]["required_action"]
        )

        self.check_finished_order(order_number, product.id, status="REVIEW")


class CSReplyViewTest(BaseCheckoutTest):
    """Test the CybersourceReplyView with fixtured requests"""

    def prepare_order(self):
        """Setup a basket"""
        product = self.create_product()

        resp = self.do_get_basket()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        basket_id = resp.data["id"]

        resp = self.do_add_to_basket(product.id)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        resp = self.do_checkout(basket_id)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        order_number = resp.data["number"]

        return order_number

    @mock.patch("oscarapicheckout.signals.order_payment_authorized.send")
    def test_invalid_signature(self, order_payment_authorized):
        """Invalid signature should result in 400 Bad Request"""
        session = self.client.session
        session.save()

        order_number = self.prepare_order()
        data = cs_factories.build_declined_token_reply_data(
            order_number, session.session_key
        )
        data = cs_factories.sign_reply_data(data)

        data["signature"] = "abcdef"

        url = reverse("cybersource-reply")
        resp = self.client.post(url, data)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            order_payment_authorized.call_count, 0, "Should not trigger signal"
        )
        self.assertEqual(
            self.do_fetch_payment_states().data["order_status"],
            "Pending",
            "Should not authorize",
        )

    @mock.patch("oscarapicheckout.signals.order_payment_authorized.send")
    def test_invalid_request_type(self, order_payment_authorized):
        """Bad request type should result in 400 Bad Request"""
        session = self.client.session
        session.save()

        order_number = self.prepare_order()
        data = cs_factories.build_declined_token_reply_data(
            order_number, session.session_key
        )

        data["req_transaction_type"] = ("payment",)

        data = cs_factories.sign_reply_data(data)
        url = reverse("cybersource-reply")
        resp = self.client.post(url, data)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            order_payment_authorized.call_count, 0, "Should not trigger signal"
        )
        self.assertEqual(
            self.do_fetch_payment_states().data["order_status"],
            "Pending",
            "Should not authorize",
        )

    @mock.patch("oscarapicheckout.signals.order_payment_authorized.send")
    def test_invalid_reference_number(self, order_payment_authorized):
        """Mismatched reference number should result in 400 Bad Request"""
        session = self.client.session
        session.save()

        order_number = self.prepare_order()
        data = cs_factories.build_accepted_token_reply_data(
            order_number + "ABC", session.session_key
        )
        data = cs_factories.sign_reply_data(data)
        url = reverse("cybersource-reply")
        resp = self.client.post(url, data)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(order_payment_authorized.call_count, 0)
        self.assertEqual(self.do_fetch_payment_states().data["order_status"], "Pending")

    @mock.patch("oscarapicheckout.signals.order_payment_authorized.send")
    def test_review_card(self, order_payment_authorized):
        """Review card should be treated like a decline and result in redirect to failure page"""
        session = self.client.session
        session.save()

        order_number = self.prepare_order()
        data = cs_factories.build_review_token_reply_data(
            order_number, session.session_key
        )
        data = cs_factories.sign_reply_data(data)
        url = reverse("cybersource-reply")

        resp = self.client.post(url, data)
        self.assertRedirects(
            resp, reverse("checkout:index"), fetch_redirect_response=False
        )

        self.assertEqual(
            order_payment_authorized.call_count, 0, "Should not trigger signal"
        )
        self.assertEqual(
            self.do_fetch_payment_states().data["order_status"], "Payment Declined"
        )

    @mock.patch("oscarapicheckout.signals.order_payment_authorized.send")
    def test_declined_card(self, order_payment_authorized):
        """Declined card should result in redirect to failure page"""
        session = self.client.session
        session.save()

        order_number = self.prepare_order()
        data = cs_factories.build_declined_token_reply_data(
            order_number, session.session_key
        )
        data = cs_factories.sign_reply_data(data)
        url = reverse("cybersource-reply")

        resp = self.client.post(url, data)
        self.assertRedirects(
            resp, reverse("checkout:index"), fetch_redirect_response=False
        )

        self.assertEqual(
            order_payment_authorized.call_count, 0, "Should not trigger signal"
        )
        self.assertEqual(
            self.do_fetch_payment_states().data["order_status"], "Payment Declined"
        )

    @mock.patch("cybersource.models.CyberSourceReply.log_soap_response")
    @mock.patch("oscarapicheckout.signals.order_payment_authorized.send")
    def test_soap_declined_auth(self, order_payment_authorized, log_soap_response):
        """Declined auth should should result in redirect to failure page"""
        log_soap_response.side_effect = mock_log_soap_response

        session = self.client.session
        session.save()

        order_number = self.prepare_order()

        data = cs_factories.build_accepted_token_reply_data(
            order_number, session.session_key
        )
        data = cs_factories.sign_reply_data(data)

        with requests_mock.mock() as rmock:
            # Setup mock auth response
            responses.mock_soap_transaction_response(rmock, responses.SOAP_AUTH_REJECT)

            url = reverse("cybersource-reply")
            resp = self.client.post(url, data)

        self.assertRedirects(
            resp, reverse("checkout:index"), fetch_redirect_response=False
        )
        self.assertEqual(
            order_payment_authorized.call_count, 0, "Should not trigger signal"
        )
        self.assertEqual(
            self.do_fetch_payment_states().data["order_status"], "Payment Declined"
        )

    @mock.patch("oscarapicheckout.signals.order_payment_authorized.send")
    @requests_mock.mock()
    def test_declined_auth(self, order_payment_authorized, rmock):
        """Declined auth should should result in redirect to failure page"""
        order_number = self.prepare_order()
        session = self.client.session
        session.save()
        data = cs_factories.build_accepted_token_reply_data(
            order_number,
            session.session_key,
        )
        data = cs_factories.sign_reply_data(data)
        responses.mock_soap_transaction_response(rmock, responses.SOAP_AUTH_REJECT)

        url = reverse("cybersource-reply")
        resp = self.client.post(url, data)

        self.assertRedirects(
            resp,
            reverse("checkout:index"),
            fetch_redirect_response=False,
        )
        self.assertEqual(
            order_payment_authorized.call_count,
            0,
            "Should not trigger signal",
        )
        self.assertEqual(
            self.do_fetch_payment_states().data["order_status"],
            "Payment Declined",
        )


class CybersourceMethodTest(BaseCheckoutTest):
    @mock.patch("cybersource.models.CyberSourceReply.log_soap_response")
    @mock.patch("cybersource.signals.pre_build_auth_request.send")
    @mock.patch("cybersource.signals.pre_build_get_token_request.send")
    @mock.patch("oscarapicheckout.signals.pre_calculate_total.send")
    def test_request_auth_soap_form_success(
        self,
        pre_calculate_total,
        pre_build_get_token_request,
        pre_build_auth_request,
        log_soap_response,
    ):
        log_soap_response.side_effect = mock_log_soap_response

        product = self.create_product()

        resp = self.do_get_basket()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        basket_id = resp.data["id"]

        resp = self.do_add_to_basket(product.id)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        # Add some taxes to the basket
        def add_taxes(sender, basket, shipping_address, **kwargs):
            for line in basket.all_lines():
                line.purchase_info.price.tax = D("0.42")

        pre_calculate_total.side_effect = add_taxes

        # Add an extra field into the request
        def add_a_field(sender, extra_fields, **kwargs):
            extra_fields["1"] = "ABC"
            extra_fields["2"] = "DEF"

        pre_build_get_token_request.side_effect = add_a_field
        pre_build_auth_request.side_effect = add_a_field

        # Checkout
        resp = self.do_checkout(basket_id)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(pre_calculate_total.call_count, 1)

        # Fetch payment state
        resp = self.do_fetch_payment_states()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(pre_build_get_token_request.call_count, 1)

        action = resp.data["payment_method_states"]["cybersource"]["required_action"]
        data = {}
        for field in action["fields"]:
            data[field["key"]] = field["value"]

        # Move onto step 2, authorize
        data["card_cvn"] = "123"
        data["card_expiry_date"] = "12-2050"
        data["card_number"] = "4111111111111111"
        data["card_type"] = "001"
        cs_resp_data = self._build_cs_get_token_response(data)
        with requests_mock.mock() as rmock:
            responses.mock_soap_transaction_response(rmock, responses.SOAP_AUTH_ACCEPT)
            # Submit
            resp = self.client.post(reverse("cybersource-reply"), cs_resp_data)
        self.assertEqual(resp.status_code, status.HTTP_302_FOUND)
        self.assertEqual(pre_build_auth_request.call_count, 1)

        # Fetch payment states again
        resp = self.do_fetch_payment_states()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["order_status"], "Authorized")
        self.assertEqual(
            resp.data["payment_method_states"]["cybersource"]["status"], "Consumed"
        )
        self.assertEqual(
            resp.data["payment_method_states"]["cybersource"]["amount"], "10.00"
        )
        self.assertIsNone(
            resp.data["payment_method_states"]["cybersource"]["required_action"]
        )

    @mock.patch("cybersource.signals.pre_build_auth_request.send")
    @mock.patch("cybersource.signals.pre_build_get_token_request.send")
    @mock.patch("oscarapicheckout.signals.pre_calculate_total.send")
    @requests_mock.mock()
    def test_request_auth_form_success(
        self,
        pre_calculate_total,
        pre_build_get_token_request,
        pre_build_auth_request,
        rmock,
    ):
        product = self.create_product()

        resp = self.do_get_basket()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        basket_id = resp.data["id"]

        resp = self.do_add_to_basket(product.id)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        # Add some taxes to the basket
        def add_taxes(sender, basket, shipping_address, **kwargs):
            for line in basket.all_lines():
                line.purchase_info.price.tax = D("0.42")

        pre_calculate_total.side_effect = add_taxes

        # Add an extra field into the request
        def add_a_field(sender, extra_fields, **kwargs):
            extra_fields["1"] = "ABC"
            extra_fields["2"] = "DEF"

        pre_build_get_token_request.side_effect = add_a_field
        pre_build_auth_request.side_effect = add_a_field

        # Checkout
        resp = self.do_checkout(basket_id)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        order_number = resp.data["number"]
        self.assertEqual(pre_calculate_total.call_count, 1)

        # Fetch payment state
        resp = self.do_fetch_payment_states()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(pre_build_get_token_request.call_count, 1)

        action = resp.data["payment_method_states"]["cybersource"]["required_action"]
        cs_url = action["url"]
        data = {}
        for field in action["fields"]:
            data[field["key"]] = field["value"]

        # Check response fields
        self.assertEqual(
            cs_url, "https://testsecureacceptance.cybersource.com/silent/pay"
        )
        self.assertEqual(data["amount"], "10.42")
        self.assertEqual(data["bill_to_address_city"], "Manhattan")
        self.assertEqual(data["bill_to_address_country"], "US")
        self.assertEqual(data["bill_to_address_line1"], "234 5th Ave")
        self.assertEqual(data["bill_to_address_line2"], "")
        self.assertEqual(data["bill_to_address_postal_code"], "10001")
        self.assertEqual(data["bill_to_address_state"], "NY")
        self.assertEqual(data["bill_to_email"], "joe@example.com")
        self.assertEqual(data["bill_to_forename"], "Joe")
        self.assertEqual(data["bill_to_phone"], "")
        self.assertEqual(data["bill_to_surname"], "Schmoe")
        self.assertEqual(data["card_cvn"], "")
        self.assertEqual(data["card_expiry_date"], "")
        self.assertEqual(data["card_number"], "")
        self.assertEqual(data["card_type"], "")
        self.assertEqual(data["currency"], "USD")
        self.assertEqual(data["customer_ip_address"], "127.0.0.1")
        self.assertEqual(data["device_fingerprint_id"], "")
        self.assertEqual(data["item_0_name"], "My Product")
        self.assertEqual(data["item_0_quantity"], "1")
        self.assertEqual(data["item_0_unit_price"], "10.42")
        self.assertEqual(data["line_item_count"], "1")
        self.assertEqual(data["locale"], "en")
        self.assertEqual(data["merchant_defined_data1"], "ABC")
        self.assertEqual(data["payment_method"], "card")
        self.assertEqual(data["reference_number"], order_number)
        self.assertEqual(data["ship_to_address_city"], "Manhattan")
        self.assertEqual(data["ship_to_address_country"], "US")
        self.assertEqual(data["ship_to_address_line1"], "234 5th Ave")
        self.assertEqual(data["ship_to_address_line2"], "")
        self.assertEqual(data["ship_to_address_postal_code"], "10001")
        self.assertEqual(data["ship_to_address_state"], "NY")
        self.assertEqual(data["ship_to_forename"], "Joe")
        self.assertEqual(data["ship_to_phone"], "17174671111")
        self.assertEqual(data["ship_to_surname"], "Schmoe")
        self.assertEqual(data["transaction_type"], "create_payment_token")
        self.assertEqual(data["shipping_method"], "lowcost")

        # Move onto step 2, authorize
        data["card_cvn"] = "123"
        data["card_expiry_date"] = "12-2050"
        data["card_number"] = "4111111111111111"
        data["card_type"] = "001"

        responses.mock_soap_transaction_response(rmock, responses.SOAP_AUTH_ACCEPT)

        cs_resp_data = self._build_cs_get_token_response(data)
        resp = self.client.post(reverse("cybersource-reply"), cs_resp_data)
        self.assertEqual(resp.status_code, status.HTTP_302_FOUND)
        self.assertEqual(pre_build_auth_request.call_count, 1)

        # Fetch payment states again
        resp = self.do_fetch_payment_states()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["order_status"], "Authorized")
        self.assertEqual(
            resp.data["payment_method_states"]["cybersource"]["status"], "Consumed"
        )
        self.assertEqual(
            resp.data["payment_method_states"]["cybersource"]["amount"], "10.00"
        )
        self.assertIsNone(
            resp.data["payment_method_states"]["cybersource"]["required_action"]
        )
