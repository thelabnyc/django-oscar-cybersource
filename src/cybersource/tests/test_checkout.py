from unittest import skipUnless

from bs4 import BeautifulSoup
from decimal import Decimal as D

from django.conf import settings
from django.core import mail
from django.urls import reverse
from django.test import tag
from mock import patch
from oscar.core.loading import get_model
from oscar.test import factories
from rest_framework import status
from rest_framework.test import APITestCase
import datetime
import requests  # Needed for external calls

from cybersource.models import CyberSourceReply
from ..constants import DECISION_REVIEW, DECISION_ACCEPT
from .utils import retry
from . import factories as cs_factories

Basket = get_model('basket', 'Basket')
Product = get_model('catalogue', 'Product')
Order = get_model('order', 'Order')

# Do we have the appropriate settings, via env vars, to perform full SOAP integration tests?
DO_SOAP = settings.CYBERSOURCE_SOAP_KEY and settings.CYBERSOURCE_MERCHANT_ID


# Mock cybersource.methods.Bluefin.log_soap_response with this
def mock_log_soap_response(request, order, response):
    # convert Mock object to dict, as the real method converts a sudsobject to dict
    response = {
        'decision': response.decision,
        'merchantReferenceCode': response.merchantReferenceCode,
    }

    response['req_reference_number'] = response.get('merchantReferenceCode', '')

    log = CyberSourceReply(
        user=request.user if request.user.is_authenticated else None,
        order=order,
        data=response)
    log.save()
    return log


class BaseCheckoutTest(APITestCase):
    fixtures = ['cybersource-test.yaml']

    def create_product(self, price=D('10.00')):
        product = factories.create_product(
            title='My Product',
            product_class='My Product Class')
        record = factories.create_stockrecord(
            currency='USD',
            product=product,
            num_in_stock=10,
            price_excl_tax=price)
        factories.create_purchase_info(record)
        return product


    def do_add_to_basket(self, product_id, quantity=1):
        url = reverse('api-basket-add-product')
        data = {
            "url": reverse('product-detail', args=[product_id]),
            "quantity": quantity
        }
        return self.client.post(url, data)


    def do_get_basket(self):
        url = reverse('api-basket')
        return self.client.get(url)


    def do_checkout(self, basket_id, extra_data={}):
        data = {
            "guest_email": "joe@example.com",
            "basket": reverse('basket-detail', args=[basket_id]),
            "shipping_address": {
                "first_name": "Joe",
                "last_name": "Schmoe",
                "line1": "234 5th Ave",
                "line4": "Manhattan",
                "postcode": "10001",
                "state": "NY",
                "country": reverse('country-detail', args=['US']),
                "phone_number": "+1 (717) 467-1111",
            },
            "billing_address": {
                "first_name": "Joe",
                "last_name": "Schmoe",
                "line1": "234 5th Ave",
                "line4": "Manhattan",
                "postcode": "10001",
                "state": "NY",
                "country": reverse('country-detail', args=['US']),
                "phone_number": "+1 (717) 467-1111",
            },
            "payment": {
                "cybersource": {
                    "enabled": True,
                }
            }
        }
        data.update(extra_data)
        url = reverse('api-checkout')
        return self.client.post(url, data, format='json')


    def do_fetch_payment_states(self):
        return self.client.get(reverse('api-payment'))


    def do_cs_reply(self, cs_resp):
        soup = BeautifulSoup(cs_resp.content, 'html.parser')
        form_data = {}
        for element in soup.find_all('input'):
            form_data[element['name']] = element['value']
        # We have the data from cybersource, send it to our cybersource callback
        url = reverse('cybersource-reply')
        return self.client.post(url, form_data)


    def do_cs_get_token(self, cs_url, fields, extra_fields={}):
        next_year = datetime.date.today().year + 1
        cs_data = {
            'card_type': '001',
            'card_number': '4111111111111111',
            'card_cvn': '123',
            'card_expiry_date': '12-{}'.format(next_year),
        }
        for field in fields:
            if not field['editable'] or field['key'] not in cs_data:
                cs_data[field['key']] = field['value']
        cs_data.update(extra_fields)
        resp = requests.post(cs_url, cs_data)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        return self.do_cs_reply(resp)


    def do_cs_auth(self, cs_url, fields, extra_fields={}):
        cs_data = {}
        for field in fields:
            if not field['editable'] or field['key'] not in cs_data:
                cs_data[field['key']] = field['value']
        cs_data.update(extra_fields)
        resp = requests.post(cs_url, cs_data)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        return self.do_cs_reply(resp)


    def check_finished_order(self, number, product_id, quantity=1, status=DECISION_ACCEPT, card_last4='1111'):
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
        self.assertEqual(payment_events[0].amount, order.total_incl_tax)

        payment_sources = order.sources.all()
        self.assertEqual(payment_sources.count(), 1)
        self.assertEqual(payment_sources[0].currency, order.currency)
        self.assertEqual(payment_sources[0].amount_allocated, order.total_incl_tax)
        self.assertEqual(payment_sources[0].amount_debited, D('0.00'))
        self.assertEqual(payment_sources[0].amount_refunded, D('0.00'))

        transactions = payment_sources[0].transactions.all()
        self.assertEqual(transactions.count(), 1)
        self.assertEqual(transactions[0].txn_type, 'Authorise')
        self.assertEqual(transactions[0].amount, order.total_incl_tax)
        self.assertEqual(transactions[0].status, status)

        self.assertEqual(transactions[0].log.order, order)
        self.assertEqual(transactions[0].log_field('req_reference_number'), order.number)
        self.assertEqual(transactions[0].token.card_last4, card_last4)
        self.assertEqual(transactions[0].token.log.order, order)
        self.assertEqual(transactions[0].token.log_field('req_reference_number'), order.number)

        self.assertEqual(len(mail.outbox), 1)

        if status == DECISION_REVIEW:
            self.assertEqual(order.notes.count(), 1, 'Should save OrderNote')
            note = order.notes.first()
            self.assertEqual(note.note_type, 'System')
            self.assertEqual(note.message,
                             'Transaction %s is currently under review. '
                             'Use Decision Manager to either accept or '
                             'reject the transaction.' % transactions[0].reference)


@tag('integration', 'slow')
class CheckoutIntegrationTest(BaseCheckoutTest):
    """Full Integration Test of Checkout using mocked SOAP integration"""

    @patch('cybersource.methods.Bluefin.log_soap_response')
    @patch('cybersource.cybersoap.CyberSourceSoap._run_transaction')
    @retry(AssertionError)
    def test_checkout_process(self, run_transaction, log_soap_response):
        """Full checkout process using minimal api calls"""
        product = self.create_product()

        resp = self.do_get_basket()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        basket_id = resp.data['id']

        resp = self.do_add_to_basket(product.id)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        resp = self.do_checkout(basket_id)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        order_number = resp.data['number']

        resp = self.do_fetch_payment_states()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['order_status'], 'Pending')
        self.assertEqual(resp.data['payment_method_states']['cybersource']['status'], 'Pending')
        self.assertEqual(resp.data['payment_method_states']['cybersource']['amount'], '10.00')
        self.assertEqual(resp.data['payment_method_states']['cybersource']['required_action']['name'], 'get-token')

        run_transaction.return_value.decision = 'ACCEPT'
        run_transaction.return_value.merchantReferenceCode = order_number
        log_soap_response.side_effect = mock_log_soap_response

        action = resp.data['payment_method_states']['cybersource']['required_action']
        resp = self.do_cs_get_token(action['url'], action['fields'])
        self.assertEqual(resp.status_code, status.HTTP_302_FOUND)

        resp = self.do_fetch_payment_states()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['order_status'], 'Authorized')
        self.assertEqual(resp.data['payment_method_states']['cybersource']['status'], 'Consumed')
        self.assertEqual(resp.data['payment_method_states']['cybersource']['amount'], '10.00')
        self.assertIsNone(resp.data['payment_method_states']['cybersource']['required_action'])

        self.check_finished_order(order_number, product.id)


    @patch('cybersource.methods.Bluefin.log_soap_response')
    @patch('cybersource.cybersoap.CyberSourceSoap._run_transaction')
    @retry(AssertionError)
    def test_decision_manager_review_auth(self, run_transaction, log_soap_response):
        product = self.create_product()

        resp = self.do_get_basket()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        basket_id = resp.data['id']

        resp = self.do_add_to_basket(product.id)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        resp = self.do_checkout(basket_id, extra_data={
            "shipping_address": {
                "first_name": "Joe",
                "last_name": "Review",  # trigger a review, per a custom rule in CyberSource admin
                "line1": "234 5th Ave",
                "line4": "Manhattan",
                "postcode": "10001",
                "state": "NY",
                "country": reverse('country-detail', args=['US']),
                "phone_number": "+1 (717) 467-1111",
            },
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        order_number = resp.data['number']

        resp = self.do_fetch_payment_states()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['order_status'], 'Pending')
        self.assertEqual(resp.data['payment_method_states']['cybersource']['status'], 'Pending')
        self.assertEqual(resp.data['payment_method_states']['cybersource']['amount'], '10.00')
        self.assertEqual(resp.data['payment_method_states']['cybersource']['required_action']['name'], 'get-token')

        run_transaction.return_value.decision = 'REVIEW'
        run_transaction.return_value.merchantReferenceCode = order_number
        log_soap_response.side_effect = mock_log_soap_response

        action = resp.data['payment_method_states']['cybersource']['required_action']
        resp = self.do_cs_get_token(action['url'], action['fields'])
        self.assertEqual(resp.status_code, status.HTTP_302_FOUND)

        resp = self.do_fetch_payment_states()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['order_status'], 'Authorized')
        self.assertEqual(resp.data['payment_method_states']['cybersource']['status'], 'Consumed')
        self.assertEqual(resp.data['payment_method_states']['cybersource']['amount'], '10.00')
        self.assertIsNone(resp.data['payment_method_states']['cybersource']['required_action'])

        self.check_finished_order(order_number, product.id, status='REVIEW')


    @patch('cybersource.methods.Bluefin.log_soap_response')
    @patch('cybersource.cybersoap.CyberSourceSoap._run_transaction')
    @retry(AssertionError)
    def test_add_product_during_auth(self, run_transaction, log_soap_response):
        """Test attempting to add a product during the authorize flow"""
        product = self.create_product()

        resp = self.do_get_basket()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        basket_id = resp.data['id']

        # Adding a product here should succeed
        resp = self.do_add_to_basket(product.id)
        basket1 = resp.data['id']
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        resp = self.do_checkout(basket_id)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        order_number = resp.data['number']

        # Adding a product here should go to a new basket, not the one we're auth'ing
        resp = self.do_add_to_basket(product.id)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        basket2 = resp.data['id']
        self.assertNotEqual(basket1, basket2)

        # Finish checkout process
        resp = self.do_fetch_payment_states()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['order_status'], 'Pending')
        self.assertEqual(resp.data['payment_method_states']['cybersource']['required_action']['name'], 'get-token')

        run_transaction.return_value.decision = 'ACCEPT'
        run_transaction.return_value.merchantReferenceCode = order_number
        log_soap_response.side_effect = mock_log_soap_response

        action = resp.data['payment_method_states']['cybersource']['required_action']
        resp = self.do_cs_get_token(action['url'], action['fields'])
        self.assertEqual(resp.status_code, status.HTTP_302_FOUND)

        resp = self.do_fetch_payment_states()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['order_status'], 'Authorized')
        self.check_finished_order(order_number, product.id)

        # Adding a product here should go to basket2, not basket1
        resp = self.do_add_to_basket(product.id)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        basket3 = resp.data['id']
        self.assertEqual(basket2, basket3)


    @retry(AssertionError)
    def test_pay_for_nothing(self):
        """Test attempting to pay for an empty basket"""
        resp = self.do_get_basket()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        basket_id = resp.data['id']

        resp = self.do_checkout(basket_id)
        self.assertEqual(resp.status_code, status.HTTP_406_NOT_ACCEPTABLE)


    @retry(AssertionError)
    def test_manipulate_total_pre_auth(self):
        """Test attempting to manipulate basket price when requesting an auth form"""
        product = self.create_product()

        resp = self.do_get_basket()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        basket_id = resp.data['id']

        resp = self.do_add_to_basket(product.id)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['total_incl_tax'], '10.00')

        resp = self.do_checkout(basket_id, extra_data={
            "total": "2.00",  # Try and get $10 of product for only $2
        })
        self.assertEqual(resp.status_code, status.HTTP_406_NOT_ACCEPTABLE)


    @patch('cybersource.methods.Bluefin.log_soap_response')
    @patch('cybersource.cybersoap.CyberSourceSoap._run_transaction')
    @retry(AssertionError)
    def test_free_product(self, run_transaction, log_soap_response):
        """Full checkout process using minimal api calls"""
        product = self.create_product(price=D('0.00'))

        resp = self.do_get_basket()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        basket_id = resp.data['id']

        resp = self.do_add_to_basket(product.id)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        resp = self.do_checkout(basket_id)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        order_number = resp.data['number']

        resp = self.do_fetch_payment_states()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['order_status'], 'Pending')
        self.assertEqual(resp.data['payment_method_states']['cybersource']['required_action']['name'], 'get-token')

        run_transaction.return_value.decision = 'ACCEPT'
        run_transaction.return_value.merchantReferenceCode = order_number
        log_soap_response.side_effect = mock_log_soap_response

        action = resp.data['payment_method_states']['cybersource']['required_action']
        resp = self.do_cs_get_token(action['url'], action['fields'])
        self.assertEqual(resp.status_code, status.HTTP_302_FOUND)

        resp = self.do_fetch_payment_states()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['order_status'], 'Authorized')
        self.assertEqual(resp.data['payment_method_states']['cybersource']['amount'], '0.00')
        self.check_finished_order(order_number, product.id)


@tag('integration', 'slow')
class CheckoutSOAPIntegrationTest(BaseCheckoutTest):
    """Full Integration Test of Checkout using real SOAP authorization"""

    @skipUnless(DO_SOAP, "No SOAP keys, skipping integration test.")
    @retry(AssertionError)
    def test_checkout_process(self):
        """Full checkout process using minimal api calls"""
        product = self.create_product()

        resp = self.do_get_basket()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        basket_id = resp.data['id']

        resp = self.do_add_to_basket(product.id)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        resp = self.do_checkout(basket_id)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        order_number = resp.data['number']

        resp = self.do_fetch_payment_states()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['order_status'], 'Pending')
        self.assertEqual(resp.data['payment_method_states']['cybersource']['status'], 'Pending')
        self.assertEqual(resp.data['payment_method_states']['cybersource']['amount'], '10.00')
        self.assertEqual(resp.data['payment_method_states']['cybersource']['required_action']['name'], 'get-token')

        action = resp.data['payment_method_states']['cybersource']['required_action']
        resp = self.do_cs_get_token(action['url'], action['fields'])
        self.assertEqual(resp.status_code, status.HTTP_302_FOUND)

        resp = self.do_fetch_payment_states()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['order_status'], 'Authorized')
        self.assertEqual(resp.data['payment_method_states']['cybersource']['status'], 'Consumed')
        self.assertEqual(resp.data['payment_method_states']['cybersource']['amount'], '10.00')
        self.assertIsNone(resp.data['payment_method_states']['cybersource']['required_action'])

        self.check_finished_order(order_number, product.id)

    @skipUnless(DO_SOAP, "No SOAP keys, skipping integration test.")
    @retry(AssertionError)
    def test_decision_manager_review_auth(self):
        product = self.create_product()

        resp = self.do_get_basket()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        basket_id = resp.data['id']

        resp = self.do_add_to_basket(product.id)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        resp = self.do_checkout(basket_id, extra_data={
            "shipping_address": {
                "first_name": "Joe",
                "last_name": "Review",  # trigger a review, per a custom rule in CyberSource admin
                "line1": "234 5th Ave",
                "line4": "Manhattan",
                "postcode": "10001",
                "state": "NY",
                "country": reverse('country-detail', args=['US']),
                "phone_number": "+1 (717) 467-1111",
            },
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        order_number = resp.data['number']

        resp = self.do_fetch_payment_states()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['order_status'], 'Pending')
        self.assertEqual(resp.data['payment_method_states']['cybersource']['status'], 'Pending')
        self.assertEqual(resp.data['payment_method_states']['cybersource']['amount'], '10.00')
        self.assertEqual(resp.data['payment_method_states']['cybersource']['required_action']['name'], 'get-token')

        action = resp.data['payment_method_states']['cybersource']['required_action']
        resp = self.do_cs_get_token(action['url'], action['fields'])
        self.assertEqual(resp.status_code, status.HTTP_302_FOUND)

        resp = self.do_fetch_payment_states()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['order_status'], 'Authorized')
        self.assertEqual(resp.data['payment_method_states']['cybersource']['status'], 'Consumed')
        self.assertEqual(resp.data['payment_method_states']['cybersource']['amount'], '10.00')
        self.assertIsNone(resp.data['payment_method_states']['cybersource']['required_action'])

        self.check_finished_order(order_number, product.id, status='REVIEW')

    @skipUnless(DO_SOAP, "No SOAP keys, skipping integration test.")
    @retry(AssertionError)
    def test_add_product_during_auth(self):
        """Test attempting to add a product during the authorize flow"""
        product = self.create_product()

        resp = self.do_get_basket()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        basket_id = resp.data['id']

        # Adding a product here should succeed
        resp = self.do_add_to_basket(product.id)
        basket1 = resp.data['id']
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        resp = self.do_checkout(basket_id)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        order_number = resp.data['number']

        # Adding a product here should go to a new basket, not the one we're auth'ing
        resp = self.do_add_to_basket(product.id)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        basket2 = resp.data['id']
        self.assertNotEqual(basket1, basket2)

        # Finish checkout process
        resp = self.do_fetch_payment_states()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['order_status'], 'Pending')
        self.assertEqual(resp.data['payment_method_states']['cybersource']['required_action']['name'], 'get-token')

        action = resp.data['payment_method_states']['cybersource']['required_action']
        resp = self.do_cs_get_token(action['url'], action['fields'])
        self.assertEqual(resp.status_code, status.HTTP_302_FOUND)

        resp = self.do_fetch_payment_states()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['order_status'], 'Authorized')
        self.check_finished_order(order_number, product.id)

        # Adding a product here should go to basket2, not basket1
        resp = self.do_add_to_basket(product.id)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        basket3 = resp.data['id']
        self.assertEqual(basket2, basket3)

    @skipUnless(DO_SOAP, "No SOAP keys, skipping integration test.")
    @retry(AssertionError)
    def test_free_product(self):
        """Full checkout process using minimal api calls"""
        product = self.create_product(price=D('0.00'))

        resp = self.do_get_basket()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        basket_id = resp.data['id']

        resp = self.do_add_to_basket(product.id)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        resp = self.do_checkout(basket_id)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        order_number = resp.data['number']

        resp = self.do_fetch_payment_states()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['order_status'], 'Pending')
        self.assertEqual(resp.data['payment_method_states']['cybersource']['required_action']['name'], 'get-token')

        action = resp.data['payment_method_states']['cybersource']['required_action']
        resp = self.do_cs_get_token(action['url'], action['fields'])
        self.assertEqual(resp.status_code, status.HTTP_302_FOUND)

        resp = self.do_fetch_payment_states()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['order_status'], 'Authorized')
        self.assertEqual(resp.data['payment_method_states']['cybersource']['amount'], '0.00')
        self.check_finished_order(order_number, product.id)


@tag('integration', 'slow')
class BluefinCheckoutIntegrationTest(BaseCheckoutTest):
    """Full Integration Test of Checkout"""

    @skipUnless(DO_SOAP, "No SOAP keys, skipping integration test.")
    @retry(AssertionError)
    def test_bluefin_checkout_ok(self):
        """Full Bluefin checkout process"""
        product = self.create_product()

        resp = self.do_get_basket()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        basket_id = resp.data['id']

        resp = self.do_add_to_basket(product.id)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        # Use VISA 4111-1111-1111-1111 with a 12/50 expiration date
        resp = self.do_checkout(basket_id, extra_data={
            "payment": {
                "bluefin": {
                    "enabled": True,
                    "payment_data": "02A600C0170018008292;4111********1111=5012?*1773F3F449C0B83318721C1837DA42160EBE"
                                    "B56AB3979BE800000000000000000000000000000000000000003834335531313837393262994996"
                                    "0E004A80000610D203"
                }
            }
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        order_number = resp.data['number']

        resp = self.do_fetch_payment_states()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['order_status'], 'Authorized')
        self.assertEqual(resp.data['payment_method_states']['bluefin']['status'], 'Consumed')
        self.assertEqual(resp.data['payment_method_states']['bluefin']['amount'], '10.00')
        self.assertIsNone(resp.data['payment_method_states']['bluefin']['required_action'])

        # don't expect a card_last4, since we're using encrypted card info
        self.check_finished_order(order_number, product.id, card_last4='')


    @skipUnless(DO_SOAP, "No SOAP keys, skipping integration test.")
    @retry(AssertionError)
    def test_bluefin_expired(self):
        """Full Bluefin checkout process with expired card"""
        product = self.create_product()

        resp = self.do_get_basket()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        basket_id = resp.data['id']

        resp = self.do_add_to_basket(product.id)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        # Use VISA 4111-1111-1111-1111 with a 12/18 expiration date
        resp = self.do_checkout(basket_id, extra_data={
            "payment": {
                "bluefin": {
                    "enabled": True,
                    "payment_data": "02A600C0170018008292;4111********1111=1812?*F34830CD08A5756641F0013117D267339592"
                                    "342CE5A3832200000000000000000000000000000000000000003834335531313837393262994996"
                                    "0E004A8000071A6803"
                }
            }
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        resp = self.do_fetch_payment_states()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['order_status'], 'Payment Declined')
        self.assertEqual(resp.data['payment_method_states']['bluefin']['status'], 'Declined')
        self.assertEqual(resp.data['payment_method_states']['bluefin']['amount'], '10.00')
        self.assertIsNone(resp.data['payment_method_states']['bluefin']['required_action'])


    @skipUnless(DO_SOAP, "No SOAP keys, skipping integration test.")
    @retry(AssertionError)
    def test_bluefin_bad_data(self):
        """Full Bluefin checkout process with bad payment data"""
        product = self.create_product()

        resp = self.do_get_basket()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        basket_id = resp.data['id']

        resp = self.do_add_to_basket(product.id)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        # Use VISA 4111-1111-1111-1111 with a 12/18 expiration date
        resp = self.do_checkout(basket_id, extra_data={
            "payment": {
                "bluefin": {
                    "enabled": True,
                    "payment_data": "FOO"
                }
            }
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        resp = self.do_fetch_payment_states()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['order_status'], 'Payment Declined')
        self.assertEqual(resp.data['payment_method_states']['bluefin']['status'], 'Declined')
        self.assertEqual(resp.data['payment_method_states']['bluefin']['amount'], '10.00')
        self.assertIsNone(resp.data['payment_method_states']['bluefin']['required_action'])


    @skipUnless(DO_SOAP, "No SOAP keys, skipping integration test.")
    @retry(AssertionError)
    def test_bluefin_decline(self):
        """Full Bluefin checkout process with decline"""
        product = self.create_product()

        resp = self.do_get_basket()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        basket_id = resp.data['id']

        resp = self.do_add_to_basket(product.id)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        # Use VISA 4111-1111-1111-1111 with a 12/50 expiration date
        resp = self.do_checkout(basket_id, extra_data={
            "payment": {
                "bluefin": {
                    "enabled": True,
                    "payment_data": "02A600C0170018008292;4111********1111=5012?*1773F3F449C0B83318721C1837DA42160EBE"
                                    "B56AB3979BE800000000000000000000000000000000000000003834335531313837393262994996"
                                    "0E004A80000610D203"
                }
            },
            "shipping_address": {
                "first_name": "Joe",
                "last_name": "Reject",  # trigger a decline, per a custom rule in CyberSource admin
                "line1": "234 5th Ave",
                "line4": "Manhattan",
                "postcode": "10001",
                "state": "NY",
                "country": reverse('country-detail', args=['US']),
                "phone_number": "+1 (717) 467-1111",
            },
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        resp = self.do_fetch_payment_states()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['order_status'], 'Payment Declined')
        self.assertEqual(resp.data['payment_method_states']['bluefin']['status'], 'Declined')
        self.assertEqual(resp.data['payment_method_states']['bluefin']['amount'], '10.00')
        self.assertIsNone(resp.data['payment_method_states']['bluefin']['required_action'])


    @skipUnless(DO_SOAP, "No SOAP keys, skipping integration test.")
    @retry(AssertionError)
    def test_bluefin_decision_manager_review_auth(self):
        """Full Bluefin checkout process with review"""
        product = self.create_product()

        resp = self.do_get_basket()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        basket_id = resp.data['id']

        resp = self.do_add_to_basket(product.id)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        # Use VISA 4111-1111-1111-1111 with a 12/50 expiration date
        resp = self.do_checkout(basket_id, extra_data={
            "payment": {
                "bluefin": {
                    "enabled": True,
                    "payment_data": "02A600C0170018008292;4111********1111=5012?*1773F3F449C0B83318721C1837DA42160EBE"
                                    "B56AB3979BE800000000000000000000000000000000000000003834335531313837393262994996"
                                    "0E004A80000610D203"
                }
            },
            "shipping_address": {
                "first_name": "Joe",
                "last_name": "Review",  # trigger a review, per a custom rule in CyberSource admin
                "line1": "234 5th Ave",
                "line4": "Manhattan",
                "postcode": "10001",
                "state": "NY",
                "country": reverse('country-detail', args=['US']),
                "phone_number": "+1 (717) 467-1111",
            },
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        order_number = resp.data['number']

        resp = self.do_fetch_payment_states()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['order_status'], 'Authorized')
        self.assertEqual(resp.data['payment_method_states']['bluefin']['status'], 'Consumed')
        self.assertEqual(resp.data['payment_method_states']['bluefin']['amount'], '10.00')
        self.assertIsNone(resp.data['payment_method_states']['bluefin']['required_action'])

        self.check_finished_order(order_number, product.id, status='REVIEW', card_last4='')


class CSReplyViewTest(BaseCheckoutTest):
    """Test the CybersourceReplyView with fixtured requests"""

    def prepare_order(self):
        """Setup a basket"""
        product = self.create_product()

        resp = self.do_get_basket()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        basket_id = resp.data['id']

        resp = self.do_add_to_basket(product.id)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        resp = self.do_checkout(basket_id)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        order_number = resp.data['number']

        return order_number


    @patch('oscarapicheckout.signals.order_payment_authorized.send')
    def test_invalid_signature(self, order_payment_authorized):
        """Invalid signature should result in 400 Bad Request"""
        order_number = self.prepare_order()
        data = cs_factories.build_declined_token_reply_data(order_number)
        data = cs_factories.sign_reply_data(data)

        data['signature'] = 'abcdef'

        url = reverse('cybersource-reply')
        resp = self.client.post(url, data)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(order_payment_authorized.call_count, 0, 'Should not trigger signal')
        self.assertEqual(self.do_fetch_payment_states().data['order_status'], 'Pending', 'Should not authorize')


    @patch('oscarapicheckout.signals.order_payment_authorized.send')
    def test_invalid_request_type(self, order_payment_authorized):
        """Bad request type should result in 400 Bad Request"""
        order_number = self.prepare_order()
        data = cs_factories.build_declined_token_reply_data(order_number)

        data["req_transaction_type"] = "payment",

        data = cs_factories.sign_reply_data(data)
        url = reverse('cybersource-reply')
        resp = self.client.post(url, data)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(order_payment_authorized.call_count, 0, 'Should not trigger signal')
        self.assertEqual(self.do_fetch_payment_states().data['order_status'], 'Pending', 'Should not authorize')


    @patch('oscarapicheckout.signals.order_payment_authorized.send')
    def test_invalid_reference_number(self, order_payment_authorized):
        """Mismatched reference number should result in 400 Bad Request"""
        order_number = self.prepare_order()
        data = cs_factories.build_accepted_token_reply_data(order_number + 'ABC')
        data = cs_factories.sign_reply_data(data)
        url = reverse('cybersource-reply')
        resp = self.client.post(url, data)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(order_payment_authorized.call_count, 0)
        self.assertEqual(self.do_fetch_payment_states().data['order_status'], 'Pending')


    @patch('oscarapicheckout.signals.order_payment_authorized.send')
    def test_review_card(self, order_payment_authorized):
        """Review card should be treated like a decline and result in redirect to failure page"""
        order_number = self.prepare_order()
        data = cs_factories.build_review_token_reply_data(order_number)
        data = cs_factories.sign_reply_data(data)
        url = reverse('cybersource-reply')

        resp = self.client.post(url, data)
        self.assertRedirects(resp, reverse('checkout:index'), fetch_redirect_response=False)

        self.assertEqual(order_payment_authorized.call_count, 0, 'Should not trigger signal')
        self.assertEqual(self.do_fetch_payment_states().data['order_status'], 'Payment Declined')


    @patch('oscarapicheckout.signals.order_payment_authorized.send')
    def test_declined_card(self, order_payment_authorized):
        """Declined card should result in redirect to failure page"""
        order_number = self.prepare_order()
        data = cs_factories.build_declined_token_reply_data(order_number)
        data = cs_factories.sign_reply_data(data)
        url = reverse('cybersource-reply')

        resp = self.client.post(url, data)
        self.assertRedirects(resp, reverse('checkout:index'), fetch_redirect_response=False)

        self.assertEqual(order_payment_authorized.call_count, 0, 'Should not trigger signal')
        self.assertEqual(self.do_fetch_payment_states().data['order_status'], 'Payment Declined')


    @skipUnless(DO_SOAP, "No SOAP keys, skipping integration test.")
    @patch('oscarapicheckout.signals.order_payment_authorized.send')
    def test_soap_declined_auth(self, order_payment_authorized):
        """Declined auth should should result in redirect to failure page"""
        order_number = self.prepare_order()

        data = cs_factories.build_accepted_token_reply_data(order_number)
        data = cs_factories.sign_reply_data(data)
        url = reverse('cybersource-reply')
        resp = self.client.post(url, data)

        self.assertRedirects(resp, reverse('checkout:index'), fetch_redirect_response=False)
        self.assertEqual(order_payment_authorized.call_count, 0, 'Should not trigger signal')
        self.assertEqual(self.do_fetch_payment_states().data['order_status'], 'Payment Declined')

    @patch('cybersource.cybersoap.CyberSourceSoap._run_transaction')
    @patch('oscarapicheckout.signals.order_payment_authorized.send')
    def test_declined_auth(self, order_payment_authorized, run_transaction):
        """Declined auth should should result in redirect to failure page"""
        order_number = self.prepare_order()

        data = cs_factories.build_accepted_token_reply_data(order_number)
        data = cs_factories.sign_reply_data(data)
        run_transaction.return_value.decision = 'REJECT'
        url = reverse('cybersource-reply')
        resp = self.client.post(url, data)

        self.assertRedirects(resp, reverse('checkout:index'), fetch_redirect_response=False)
        self.assertEqual(order_payment_authorized.call_count, 0, 'Should not trigger signal')
        self.assertEqual(self.do_fetch_payment_states().data['order_status'], 'Payment Declined')


class CybersourceMethodTest(BaseCheckoutTest):

    @skipUnless(DO_SOAP, "No SOAP keys, skipping integration test.")
    @patch('cybersource.signals.pre_build_auth_request.send')
    @patch('cybersource.signals.pre_build_get_token_request.send')
    @patch('oscarapicheckout.signals.pre_calculate_total.send')
    def test_request_auth_soap_form_success(self, pre_calculate_total, pre_build_get_token_request, pre_build_auth_request):
        product = self.create_product()

        resp = self.do_get_basket()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        basket_id = resp.data['id']

        resp = self.do_add_to_basket(product.id)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        # Add some taxes to the basket
        def add_taxes(sender, basket, shipping_address, **kwargs):
            for line in basket.all_lines():
                line.purchase_info.price.tax = D('0.42')
        pre_calculate_total.side_effect = add_taxes

        # Add an extra field into the request
        def add_a_field(sender, extra_fields, **kwargs):
            extra_fields['merchant_defined_data1'] = 'ABC'
            extra_fields['merchant_defined_data2'] = 'DEF'
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

        action = resp.data['payment_method_states']['cybersource']['required_action']
        cs_url = action['url']
        data = {}
        for field in action['fields']:
            data[field['key']] = field['value']

        # Move onto step 2, authorize
        data['card_cvn'] = '123'
        data['card_expiry_date'] = '12-2020'
        data['card_number'] = '4111111111111111'
        data['card_type'] = '001'
        resp = requests.post(cs_url, data)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        resp = self.do_cs_reply(resp)
        self.assertEqual(resp.status_code, status.HTTP_302_FOUND)
        self.assertEqual(pre_build_auth_request.call_count, 1)

        # Fetch payment states again
        resp = self.do_fetch_payment_states()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['order_status'], 'Authorized')
        self.assertEqual(resp.data['payment_method_states']['cybersource']['status'], 'Consumed')
        self.assertEqual(resp.data['payment_method_states']['cybersource']['amount'], '10.42')
        self.assertIsNone(resp.data['payment_method_states']['cybersource']['required_action'])

    @patch('cybersource.cybersoap.CyberSourceSoap._run_transaction')
    @patch('cybersource.signals.pre_build_auth_request.send')
    @patch('cybersource.signals.pre_build_get_token_request.send')
    @patch('oscarapicheckout.signals.pre_calculate_total.send')
    def test_request_auth_form_success(self, pre_calculate_total, pre_build_get_token_request, pre_build_auth_request,
                                       run_transaction):
        product = self.create_product()

        resp = self.do_get_basket()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        basket_id = resp.data['id']

        resp = self.do_add_to_basket(product.id)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        # Add some taxes to the basket
        def add_taxes(sender, basket, shipping_address, **kwargs):
            for line in basket.all_lines():
                line.purchase_info.price.tax = D('0.42')

        pre_calculate_total.side_effect = add_taxes

        # Add an extra field into the request
        def add_a_field(sender, extra_fields, **kwargs):
            extra_fields['merchant_defined_data1'] = 'ABC'
            extra_fields['merchant_defined_data2'] = 'DEF'

        pre_build_get_token_request.side_effect = add_a_field
        pre_build_auth_request.side_effect = add_a_field

        # Checkout
        resp = self.do_checkout(basket_id)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        order_number = resp.data['number']
        self.assertEqual(pre_calculate_total.call_count, 1)

        # Fetch payment state
        resp = self.do_fetch_payment_states()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(pre_build_get_token_request.call_count, 1)

        action = resp.data['payment_method_states']['cybersource']['required_action']
        cs_url = action['url']
        data = {}
        for field in action['fields']:
            data[field['key']] = field['value']

        # Check response fields
        self.assertEqual(cs_url, 'https://testsecureacceptance.cybersource.com/silent/pay')
        self.assertEqual(data['amount'], '10.42')
        self.assertEqual(data['bill_to_address_city'], 'Manhattan')
        self.assertEqual(data['bill_to_address_country'], 'US')
        self.assertEqual(data['bill_to_address_line1'], '234 5th Ave')
        self.assertEqual(data['bill_to_address_line2'], '')
        self.assertEqual(data['bill_to_address_postal_code'], '10001')
        self.assertEqual(data['bill_to_address_state'], 'NY')
        self.assertEqual(data['bill_to_email'], 'joe@example.com')
        self.assertEqual(data['bill_to_forename'], 'Joe')
        self.assertEqual(data['bill_to_phone'], '')
        self.assertEqual(data['bill_to_surname'], 'Schmoe')
        self.assertEqual(data['card_cvn'], '')
        self.assertEqual(data['card_expiry_date'], '')
        self.assertEqual(data['card_number'], '')
        self.assertEqual(data['card_type'], '')
        self.assertEqual(data['currency'], 'USD')
        self.assertEqual(data['customer_ip_address'], '127.0.0.1')
        self.assertEqual(data['device_fingerprint_id'], '')
        self.assertEqual(data['item_0_name'], 'My Product')
        self.assertEqual(data['item_0_quantity'], '1')
        self.assertEqual(data['item_0_unit_price'], '10.42')
        self.assertEqual(data['line_item_count'], '1')
        self.assertEqual(data['locale'], 'en')
        self.assertEqual(data['merchant_defined_data1'], 'ABC')
        self.assertEqual(data['payment_method'], 'card')
        self.assertEqual(data['reference_number'], order_number)
        self.assertEqual(data['ship_to_address_city'], 'Manhattan')
        self.assertEqual(data['ship_to_address_country'], 'US')
        self.assertEqual(data['ship_to_address_line1'], '234 5th Ave')
        self.assertEqual(data['ship_to_address_line2'], '')
        self.assertEqual(data['ship_to_address_postal_code'], '10001')
        self.assertEqual(data['ship_to_address_state'], 'NY')
        self.assertEqual(data['ship_to_forename'], 'Joe')
        self.assertEqual(data['ship_to_phone'], '17174671111')
        self.assertEqual(data['ship_to_surname'], 'Schmoe')
        self.assertEqual(data['transaction_type'], 'create_payment_token')
        self.assertEqual(data['shipping_method'], 'lowcost')

        # Move onto step 2, authorize
        data['card_cvn'] = '123'
        data['card_expiry_date'] = '12-2020'
        data['card_number'] = '4111111111111111'
        data['card_type'] = '001'
        resp = requests.post(cs_url, data)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        run_transaction.return_value.decision = 'ACCEPT'
        resp = self.do_cs_reply(resp)
        self.assertEqual(resp.status_code, status.HTTP_302_FOUND)
        self.assertEqual(pre_build_auth_request.call_count, 1)

        # Fetch payment states again
        resp = self.do_fetch_payment_states()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['order_status'], 'Authorized')
        self.assertEqual(resp.data['payment_method_states']['cybersource']['status'], 'Consumed')
        self.assertEqual(resp.data['payment_method_states']['cybersource']['amount'], '10.42')
        self.assertIsNone(resp.data['payment_method_states']['cybersource']['required_action'])
