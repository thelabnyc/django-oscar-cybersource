from bs4 import BeautifulSoup
from decimal import Decimal as D
from django.core import mail
from django.core.urlresolvers import reverse
from mock import patch
from oscar.core.loading import get_model
from oscar.test import factories
from rest_framework import status
from rest_framework.test import APITestCase
import datetime
import requests  # Needed for external calls

from ..constants import CHECKOUT_ORDER_ID
from . import factories as cs_factories

Basket = get_model('basket', 'Basket')
Product = get_model('catalogue', 'Product')
Order = get_model('order', 'Order')


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


    def check_finished_order(self, number, product_id, quantity=1):
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
        self.assertEqual(transactions[0].status, 'ACCEPT')

        self.assertEqual(transactions[0].log.order, order)
        self.assertEqual(transactions[0].log_field('req_reference_number'), order.number)
        self.assertEqual(transactions[0].token.card_last4, '1111')
        self.assertEqual(transactions[0].token.log.order, order)
        self.assertEqual(transactions[0].token.log_field('req_reference_number'), order.number)

        self.assertEqual(len(mail.outbox), 1)



class CheckoutIntegrationTest(BaseCheckoutTest):
    """Full Integration Test of Checkout"""

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
        self.assertEqual(resp.data['order_status'], 'Pending')
        self.assertEqual(resp.data['payment_method_states']['cybersource']['status'], 'Pending')
        self.assertEqual(resp.data['payment_method_states']['cybersource']['amount'], '10.00')
        self.assertEqual(resp.data['payment_method_states']['cybersource']['required_action']['name'], 'authorize')

        action = resp.data['payment_method_states']['cybersource']['required_action']
        resp = self.do_cs_auth(action['url'], action['fields'])
        self.assertEqual(resp.status_code, status.HTTP_302_FOUND)

        resp = self.do_fetch_payment_states()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['order_status'], 'Authorized')
        self.assertEqual(resp.data['payment_method_states']['cybersource']['status'], 'Complete')
        self.assertEqual(resp.data['payment_method_states']['cybersource']['amount'], '10.00')
        self.assertIsNone(resp.data['payment_method_states']['cybersource']['required_action'])

        self.check_finished_order(order_number, product.id)


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
        self.assertEqual(resp.data['order_status'], 'Pending')
        self.assertEqual(resp.data['payment_method_states']['cybersource']['required_action']['name'], 'authorize')

        action = resp.data['payment_method_states']['cybersource']['required_action']
        resp = self.do_cs_auth(action['url'], action['fields'])
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


    def test_pay_for_nothing(self):
        """Test attempting to pay for an empty basket"""
        resp = self.do_get_basket()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        basket_id = resp.data['id']

        resp = self.do_checkout(basket_id)
        self.assertEqual(resp.status_code, status.HTTP_406_NOT_ACCEPTABLE)


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


    def test_manipulate_total_during_auth(self):
        """Test attempting to manipulate basket price when requesting auth from CyberSource"""
        product = self.create_product()

        resp = self.do_get_basket()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        basket_id = resp.data['id']

        resp = self.do_add_to_basket(product.id)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['total_incl_tax'], '10.00')

        resp = self.do_checkout(basket_id)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        resp = self.do_fetch_payment_states()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['order_status'], 'Pending')
        self.assertEqual(resp.data['payment_method_states']['cybersource']['status'], 'Pending')
        self.assertEqual(resp.data['payment_method_states']['cybersource']['amount'], '10.00')
        self.assertEqual(resp.data['payment_method_states']['cybersource']['required_action']['name'], 'get-token')

        action = resp.data['payment_method_states']['cybersource']['required_action']
        self.do_cs_get_token(action['url'], action['fields'])

        resp = self.do_fetch_payment_states()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['order_status'], 'Pending')
        self.assertEqual(resp.data['payment_method_states']['cybersource']['status'], 'Pending')
        self.assertEqual(resp.data['payment_method_states']['cybersource']['amount'], '10.00')
        self.assertEqual(resp.data['payment_method_states']['cybersource']['required_action']['name'], 'authorize')

        action = resp.data['payment_method_states']['cybersource']['required_action']
        next_year = datetime.date.today().year + 1
        cs_data = {
            'card_type': '001',
            'card_number': '4111111111111111',
            'card_cvn': '123',
            'card_expiry_date': '12-{}'.format(next_year),
            'bill_to_forename': 'Testy',
            'bill_to_surname': 'McUnitTest',
            'bill_to_address_line1': '234 5th Ave',
            'bill_to_address_line2': 'apt 5',
            'bill_to_address_city': 'Manhattan',
            'bill_to_address_state': 'NY',
            'bill_to_address_postal_code': '10001',
            'bill_to_address_country': 'US',
            'bill_to_phone': '17174671111',
        }
        for field in action['fields']:
            if not field['editable'] or field['key'] not in cs_data:
                cs_data[field['key']] = field['value']

        cs_data['amount'] = '2.00'  # Try and change the auth amount

        resp = requests.post(action['url'], cs_data)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


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
        self.assertEqual(resp.data['order_status'], 'Pending')
        self.assertEqual(resp.data['payment_method_states']['cybersource']['required_action']['name'], 'authorize')

        action = resp.data['payment_method_states']['cybersource']['required_action']
        resp = self.do_cs_auth(action['url'], action['fields'])
        self.assertEqual(resp.status_code, status.HTTP_302_FOUND)

        resp = self.do_fetch_payment_states()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['order_status'], 'Authorized')
        self.assertEqual(resp.data['payment_method_states']['cybersource']['amount'], '0.00')
        self.check_finished_order(order_number, product.id)



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
    def test_duplicate_transaction_id(self, order_payment_authorized):
        """Duplicate Transaction ID should result in redirect to the success page"""
        order_number = self.prepare_order()
        self.assertEqual(order_payment_authorized.call_count, 0)
        self.assertEqual(self.do_fetch_payment_states().data['order_status'], 'Pending', 'Should not authorize')

        data = cs_factories.build_accepted_token_reply_data(order_number)
        data = cs_factories.sign_reply_data(data)
        url = reverse('cybersource-reply')
        resp = self.client.post(url, data)

        self.assertRedirects(resp, reverse('checkout:index'), fetch_redirect_response=False)
        self.assertEqual(order_payment_authorized.call_count, 0)
        self.assertEqual(self.do_fetch_payment_states().data['order_status'], 'Pending')

        data = cs_factories.build_accepted_auth_reply_data(order_number)
        data = cs_factories.sign_reply_data(data)
        url = reverse('cybersource-reply')
        resp = self.client.post(url, data)

        self.assertRedirects(resp, reverse('checkout:thank-you'), fetch_redirect_response=False)
        self.assertEqual(order_payment_authorized.call_count, 1)
        self.assertEqual(self.do_fetch_payment_states().data['order_status'], 'Authorized')

        resp = self.client.post(url, data)
        self.assertRedirects(resp, reverse('checkout:thank-you'), fetch_redirect_response=False)
        self.assertEqual(order_payment_authorized.call_count, 1)
        self.assertEqual(self.do_fetch_payment_states().data['order_status'], 'Authorized')


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
    def test_declined_card(self, order_payment_authorized):
        """Declined card should should result in redirect to failure page"""
        order_number = self.prepare_order()
        data = cs_factories.build_declined_token_reply_data(order_number)
        data = cs_factories.sign_reply_data(data)
        url = reverse('cybersource-reply')

        resp = self.client.post(url, data)
        self.assertRedirects(resp, reverse('checkout:index'), fetch_redirect_response=False)

        self.assertEqual(order_payment_authorized.call_count, 0, 'Should not trigger signal')
        self.assertEqual(self.do_fetch_payment_states().data['order_status'], 'Payment Declined')


    @patch('oscarapicheckout.signals.order_payment_authorized.send')
    def test_declined_auth(self, order_payment_authorized):
        """Declined auth should should result in redirect to failure page"""
        order_number = self.prepare_order()

        data = cs_factories.build_accepted_token_reply_data(order_number)
        data = cs_factories.sign_reply_data(data)
        url = reverse('cybersource-reply')
        resp = self.client.post(url, data)

        self.assertRedirects(resp, reverse('checkout:index'), fetch_redirect_response=False)
        self.assertEqual(order_payment_authorized.call_count, 0, 'Should not trigger signal')
        self.assertEqual(self.do_fetch_payment_states().data['order_status'], 'Pending')

        data = cs_factories.build_declined_auth_reply_data(order_number)
        data = cs_factories.sign_reply_data(data)
        url = reverse('cybersource-reply')
        resp = self.client.post(url, data)

        self.assertRedirects(resp, reverse('checkout:index'), fetch_redirect_response=False)
        self.assertEqual(order_payment_authorized.call_count, 0, 'Should not trigger signal')
        self.assertEqual(self.do_fetch_payment_states().data['order_status'], 'Payment Declined')


    @patch('oscarapicheckout.signals.order_payment_authorized.send')
    def test_decision_manager_review_auth(self, order_payment_authorized):
        """Reviewed auth should create an order and redirect to the success page, but flag the transaction as under review."""
        """Successful authorization should create an order and redirect to the success page"""
        order_number = self.prepare_order()

        data = cs_factories.build_accepted_token_reply_data(order_number)
        data = cs_factories.sign_reply_data(data)
        url = reverse('cybersource-reply')
        self.assertEqual(order_payment_authorized.call_count, 0)
        resp = self.client.post(url, data)

        data = cs_factories.build_dmreview_auth_reply_data(order_number)
        data = cs_factories.sign_reply_data(data)
        url = reverse('cybersource-reply')
        self.assertEqual(order_payment_authorized.call_count, 0)
        resp = self.client.post(url, data)

        self.assertRedirects(resp, reverse('checkout:thank-you'))

        self.assertEqual(self.do_fetch_payment_states().data['order_status'], 'Authorized')
        self.assertEqual(order_payment_authorized.call_count, 1, 'Should trigger order_payment_authorized signal')

        order = order_payment_authorized.call_args[1]['order']
        self.assertEqual(order.status, 'Authorized', 'Should set order status')
        self.assertEqual(order.number, order_number, 'Should use order number from CS request')

        session = self.client.session
        self.assertEquals(session[CHECKOUT_ORDER_ID], order.id, 'Should save order_id in session')

        self.assertEqual(order.sources.count(), 1, 'Should save PaymentSource')
        source = order.sources.first()
        self.assertEqual(source.currency, 'USD')
        self.assertEqual(source.amount_allocated, D('99.99'))
        self.assertEqual(source.amount_refunded, D('0.00'))
        self.assertEqual(source.amount_debited, D('0.00'))

        self.assertEqual(source.transactions.count(), 1, 'Should save Transaction')
        transaction = source.transactions.first()
        self.assertEqual(transaction.token.masked_card_number, 'xxxxxxxxxxxx1111')
        self.assertEqual(transaction.token.card_type, '001')
        self.assertEqual(transaction.txn_type, 'Authorise')
        self.assertEqual(transaction.amount, D('99.99'))
        self.assertEqual(transaction.reference, data['transaction_id'])
        self.assertEqual(transaction.status, 'REVIEW')
        self.assertEqual(transaction.request_token, data['request_token'])

        self.assertEqual(order.payment_events.count(), 1, 'Should save PaymentEvent')
        event = order.payment_events.first()
        self.assertEqual(event.amount, D('99.99'))
        self.assertEqual(event.reference, data['transaction_id'])
        self.assertEqual(event.event_type.name, 'Authorise')

        self.assertEqual(event.line_quantities.count(), 1, 'Should save PaymentEventQuantity')
        lq = event.line_quantities.first()
        self.assertEqual(lq.line, order.lines.first())
        self.assertEqual(lq.quantity, 1)

        self.assertEqual(order.notes.count(), 1, 'Should save OrderNote')
        note = order.notes.first()
        self.assertEqual(note.note_type, 'System')
        self.assertEqual(note.message,
            'Transaction %s is currently under review. Use Decision Manager to either accept or reject the transaction.' % transaction.reference)


    @patch('oscarapicheckout.signals.order_payment_authorized.send')
    def test_success(self, order_payment_authorized):
        """Successful authorization should create an order and redirect to the success page"""
        order_number = self.prepare_order()

        data = cs_factories.build_accepted_token_reply_data(order_number)
        data = cs_factories.sign_reply_data(data)
        url = reverse('cybersource-reply')
        self.assertEqual(order_payment_authorized.call_count, 0)
        resp = self.client.post(url, data)

        data = cs_factories.build_accepted_auth_reply_data(order_number)
        data = cs_factories.sign_reply_data(data)
        url = reverse('cybersource-reply')
        self.assertEqual(order_payment_authorized.call_count, 0)
        resp = self.client.post(url, data)

        self.assertRedirects(resp, reverse('checkout:thank-you'))

        self.assertEqual(self.do_fetch_payment_states().data['order_status'], 'Authorized')
        self.assertEqual(order_payment_authorized.call_count, 1, 'Should trigger order_payment_authorized signal')

        order = order_payment_authorized.call_args[1]['order']
        self.assertEqual(order.status, 'Authorized', 'Should set order status')
        self.assertEqual(order.number, order_number, 'Should use order number from CS request')

        session = self.client.session
        self.assertEquals(session[CHECKOUT_ORDER_ID], order.id, 'Should save order_id in session')

        self.assertEqual(order.sources.count(), 1, 'Should save PaymentSource')
        source = order.sources.first()
        self.assertEqual(source.currency, 'USD')
        self.assertEqual(source.amount_allocated, D('99.99'))
        self.assertEqual(source.amount_refunded, D('0.00'))
        self.assertEqual(source.amount_debited, D('0.00'))

        self.assertEqual(source.transactions.count(), 1, 'Should save Transaction')
        transaction = source.transactions.first()
        self.assertEqual(transaction.token.masked_card_number, 'xxxxxxxxxxxx1111')
        self.assertEqual(transaction.token.card_type, '001')
        self.assertEqual(transaction.txn_type, 'Authorise')
        self.assertEqual(transaction.amount, D('99.99'))
        self.assertEqual(transaction.reference, data['transaction_id'])
        self.assertEqual(transaction.status, 'ACCEPT')
        self.assertEqual(transaction.request_token, data['request_token'])

        self.assertEqual(order.payment_events.count(), 1, 'Should save PaymentEvent')
        event = order.payment_events.first()
        self.assertEqual(event.amount, D('99.99'))
        self.assertEqual(event.reference, data['transaction_id'])
        self.assertEqual(event.event_type.name, 'Authorise')

        self.assertEqual(event.line_quantities.count(), 1, 'Should save PaymentEventQuantity')
        lq = event.line_quantities.first()
        self.assertEqual(lq.line, order.lines.first())
        self.assertEqual(lq.quantity, 1)


    def test_send_mail(self):
        """Successful authorization should send an email"""
        order_number = self.prepare_order()

        data = cs_factories.build_accepted_token_reply_data(order_number)
        data = cs_factories.sign_reply_data(data)
        url = reverse('cybersource-reply')
        resp = self.client.post(url, data)

        data = cs_factories.build_accepted_auth_reply_data(order_number)
        data = cs_factories.sign_reply_data(data)
        url = reverse('cybersource-reply')
        resp = self.client.post(url, data)

        self.assertRedirects(resp, reverse('checkout:thank-you'))

        self.assertEqual(self.do_fetch_payment_states().data['order_status'], 'Authorized')
        self.assertEqual(len(mail.outbox), 1, 'Should send email')



class CybersourceMethodTest(BaseCheckoutTest):
    @patch('cybersource.signals.pre_build_auth_request.send')
    @patch('cybersource.signals.pre_build_get_token_request.send')
    @patch('oscarapicheckout.signals.pre_calculate_total.send')
    def test_request_auth_form_success(self, pre_calculate_total, pre_build_get_token_request, pre_build_auth_request):
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
            extra_fields['my_custom_field'] = 'ABC'
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
        self.assertEquals(data['amount'], '10.42')
        self.assertEquals(data['bill_to_address_city'], 'Manhattan')
        self.assertEquals(data['bill_to_address_country'], 'US')
        self.assertEquals(data['bill_to_address_line1'], '234 5th Ave')
        self.assertEquals(data['bill_to_address_line2'], '')
        self.assertEquals(data['bill_to_address_postal_code'], '10001')
        self.assertEquals(data['bill_to_address_state'], 'NY')
        self.assertEquals(data['bill_to_email'], 'joe@example.com')
        self.assertEquals(data['bill_to_forename'], 'Joe')
        self.assertEquals(data['bill_to_phone'], '')
        self.assertEquals(data['bill_to_surname'], 'Schmoe')
        self.assertEquals(data['card_cvn'], '')
        self.assertEquals(data['card_expiry_date'], '')
        self.assertEquals(data['card_number'], '')
        self.assertEquals(data['card_type'], '')
        self.assertEquals(data['currency'], 'USD')
        self.assertEquals(data['customer_ip_address'], '127.0.0.1')
        self.assertEquals(data['device_fingerprint_id'], '')
        self.assertEquals(data['item_0_name'], 'My Product')
        self.assertEquals(data['item_0_quantity'], '1')
        self.assertEquals(data['item_0_unit_price'], '10.42')
        self.assertEquals(data['line_item_count'], '1')
        self.assertEquals(data['locale'], 'en')
        self.assertEquals(data['my_custom_field'], 'ABC')
        self.assertEquals(data['payment_method'], 'card')
        self.assertEquals(data['reference_number'], order_number)
        self.assertEquals(data['ship_to_address_city'], 'Manhattan')
        self.assertEquals(data['ship_to_address_country'], 'US')
        self.assertEquals(data['ship_to_address_line1'], '234 5th Ave')
        self.assertEquals(data['ship_to_address_line2'], '')
        self.assertEquals(data['ship_to_address_postal_code'], '10001')
        self.assertEquals(data['ship_to_address_state'], 'NY')
        self.assertEquals(data['ship_to_forename'], 'Joe')
        self.assertEquals(data['ship_to_phone'], '17174671111')
        self.assertEquals(data['ship_to_surname'], 'Schmoe')
        self.assertEquals(data['transaction_type'], 'create_payment_token')

        # Move onto step 2, authorize
        data['card_cvn'] = '123'
        data['card_expiry_date'] = '12-2020'
        data['card_number'] = '4111111111111111'
        data['card_type'] = '001'
        resp = requests.post(cs_url, data)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        resp = self.do_cs_reply(resp)
        self.assertEquals(resp.status_code, status.HTTP_302_FOUND)
        self.assertEqual(pre_build_auth_request.call_count, 1)

        # Fetch payment states again
        resp = self.do_fetch_payment_states()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        action = resp.data['payment_method_states']['cybersource']['required_action']
        cs_url = action['url']
        data = {}
        for field in action['fields']:
            data[field['key']] = field['value']

        # Check response fields
        self.assertEqual(cs_url, 'https://testsecureacceptance.cybersource.com/silent/pay')
        self.assertEquals(data['amount'], '10.42')
        self.assertEquals(data['bill_to_address_city'], 'Manhattan')
        self.assertEquals(data['bill_to_address_country'], 'US')
        self.assertEquals(data['bill_to_address_line1'], '234 5th Ave')
        self.assertEquals(data['bill_to_address_line2'], '')
        self.assertEquals(data['bill_to_address_postal_code'], '10001')
        self.assertEquals(data['bill_to_address_state'], 'NY')
        self.assertEquals(data['bill_to_email'], 'joe@example.com')
        self.assertEquals(data['bill_to_forename'], 'Joe')
        self.assertEquals(data['bill_to_phone'], '')
        self.assertEquals(data['bill_to_surname'], 'Schmoe')
        self.assertEquals(data['currency'], 'USD')
        self.assertEquals(data['customer_ip_address'], '127.0.0.1')
        self.assertEquals(data['device_fingerprint_id'], '')
        self.assertEquals(data['item_0_name'], 'My Product')
        self.assertEquals(data['item_0_quantity'], '1')
        self.assertEquals(data['item_0_unit_price'], '10.42')
        self.assertEquals(data['line_item_count'], '1')
        self.assertEquals(data['locale'], 'en')
        self.assertEquals(data['my_custom_field'], 'ABC')
        self.assertEquals(data['payment_method'], 'card')
        self.assertEquals(data['reference_number'], order_number)
        self.assertEquals(data['ship_to_address_city'], 'Manhattan')
        self.assertEquals(data['ship_to_address_country'], 'US')
        self.assertEquals(data['ship_to_address_line1'], '234 5th Ave')
        self.assertEquals(data['ship_to_address_line2'], '')
        self.assertEquals(data['ship_to_address_postal_code'], '10001')
        self.assertEquals(data['ship_to_address_state'], 'NY')
        self.assertEquals(data['ship_to_forename'], 'Joe')
        self.assertEquals(data['ship_to_phone'], '17174671111')
        self.assertEquals(data['ship_to_surname'], 'Schmoe')
        self.assertEquals(data['transaction_type'], 'authorization')
        self.assertIsNotNone(data['payment_token'])
