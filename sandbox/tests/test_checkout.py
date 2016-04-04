from bs4 import BeautifulSoup
from decimal import Decimal as D
from django.core import mail
from django.core.urlresolvers import reverse
from oscar.core.loading import get_model
from oscar.test import factories
from rest_framework.test import APITestCase
import datetime
import requests # Needed for external calls!

Product = get_model('catalogue', 'Product')
Order = get_model('order', 'Order')


class CheckoutAPITest(APITestCase):
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

    def do_sign_auth_request(self, basket_id=None, data=None):
        if data is None:
            data = {
                "guest_email": "herp@example.com",
                "basket": reverse('basket-detail', args=[basket_id]),
                "shipping_address": {
                    "first_name": "fadsf",
                    "last_name": "fad",
                    "line1": "234 5th Ave",
                    "line4": "Manhattan",
                    "postcode": "10001",
                    "state": "NY",
                    "country": reverse('country-detail', args=['US']),
                    "phone_number": "+1 (717) 467-1111",
                }
            }
        url = reverse('cybersource-sign-auth-request')
        res = self.client.post(url, data, format='json')
        self.assertEqual(res.status_code, 200)

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
        for field in res.data['fields']:
            if not field['editable'] or field['key'] not in cs_data:
                cs_data[field['key']] = field['value']
        cs_url = res.data['url']
        return cs_url, cs_data

    def do_cybersource_post(self, cs_url, cs_data):
        res = requests.post(cs_url, cs_data)
        self.assertEqual(res.status_code, 200)

        soup = BeautifulSoup(res.content, 'html.parser')
        form_data = {}
        for element in soup.find_all('input'):
            form_data[element['name']] = element['value']

        # We have the data from cybersource, send it to our cybersource callback
        url = reverse('cybersource-reply')
        return self.client.post(url, form_data)

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

        self.assertEqual(transactions[0].log_field('req_reference_number'), order.number)
        self.assertEqual(transactions[0].token.card_last4, '1111')

        self.assertEqual(len(mail.outbox), 1)


    def test_checkout_process(self):
        """Full checkout process using minimal api calls"""
        product = self.create_product()

        res = self.do_get_basket()
        self.assertEqual(res.status_code, 200)
        basket_id = res.data['id']

        res = self.do_add_to_basket(product.id)
        self.assertEqual(res.status_code, 200)

        cs_url, cs_data = self.do_sign_auth_request(basket_id)

        res = self.do_cybersource_post(cs_url, cs_data)
        self.assertEqual(res.status_code, 302)
        self.check_finished_order(cs_data['reference_number'], product.id)


    def test_add_product_during_auth(self):
        """Test attempting to add a product during the authorize flow"""
        product = self.create_product()

        res = self.do_get_basket()
        self.assertEqual(res.status_code, 200)
        basket_id = res.data['id']

        # Adding a product here should succeed
        res = self.do_add_to_basket(product.id)
        basket1 = res.data['id']
        self.assertEqual(res.status_code, 200)

        cs_url, cs_data = self.do_sign_auth_request(basket_id)

        # Adding a product here should go to a new basket, not the one we're auth'ing
        res = self.do_add_to_basket(product.id)
        self.assertEqual(res.status_code, 200)
        basket2 = res.data['id']
        self.assertNotEqual(basket1, basket2)

        res = self.do_cybersource_post(cs_url, cs_data)
        self.assertEqual(res.status_code, 302)
        self.check_finished_order(cs_data['reference_number'], product.id)

        # Adding a product here should go to basket2, not basket1
        res = self.do_add_to_basket(product.id)
        self.assertEqual(res.status_code, 200)
        basket3 = res.data['id']
        self.assertEqual(basket2, basket3)


    def test_pay_for_nothing(self):
        """Test attempting to pay for an empty basket"""
        res = self.do_get_basket()
        self.assertEqual(res.status_code, 200)
        basket_id = res.data['id']

        data = {
            "guest_email": "herp@example.com",
            "basket": reverse('basket-detail', args=[basket_id]),
            "shipping_address": {
                "first_name": "fadsf",
                "last_name": "fad",
                "line1": "234 5th Ave",
                "line4": "Manhattan",
                "postcode": "10001",
                "state": "NY",
                "country": reverse('country-detail', args=['US']),
                "phone_number": "+1 (717) 467-1111",
            }
        }
        url = reverse('cybersource-sign-auth-request')
        res = self.client.post(url, data, format='json')
        self.assertEqual(res.status_code, 406)


    def test_manipulate_total_pre_auth(self):
        """Test attempting to manipulate basket price when requesting an auth form"""
        product = self.create_product()

        res = self.do_get_basket()
        self.assertEqual(res.status_code, 200)
        basket_id = res.data['id']

        res = self.do_add_to_basket(product.id)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['total_incl_tax'], '10.00')

        url = reverse('cybersource-sign-auth-request')
        data = {
            "guest_email": "herp@example.com",
            "basket": reverse('basket-detail', args=[basket_id]),
            "total": "2.00", # Try and get $10 of product for only $2
            "shipping_address": {
                "first_name": "fadsf",
                "last_name": "fad",
                "line1": "234 5th Ave",
                "line4": "Manhattan",
                "postcode": "10001",
                "state": "NY",
                "country": reverse('country-detail', args=['US']),
                "phone_number": "+1 (717) 467-1111",
            }
        }
        res = self.client.post(url, data, format='json')
        self.assertEqual(res.status_code, 406)


    def test_manipulate_total_during_auth(self):
        """Test attempting to manipulate basket price when requesting auth from CyberSource"""
        product = self.create_product()

        res = self.do_get_basket()
        self.assertEqual(res.status_code, 200)
        basket_id = res.data['id']

        res = self.do_add_to_basket(product.id)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['total_incl_tax'], '10.00')

        cs_url, cs_data = self.do_sign_auth_request(basket_id)

        cs_data['amount'] = '2.00'
        res = requests.post(cs_url, cs_data)
        self.assertEqual(res.status_code, 403)


    def test_free_product(self):
        """Full checkout process using minimal api calls"""
        product = self.create_product(price=D('0.00'))

        res = self.do_get_basket()
        self.assertEqual(res.status_code, 200)
        basket_id = res.data['id']

        res = self.do_add_to_basket(product.id)
        self.assertEqual(res.status_code, 200)

        cs_url, cs_data = self.do_sign_auth_request(basket_id)

        self.assertEqual(cs_data['amount'], '0.00')

        res = self.do_cybersource_post(cs_url, cs_data)
        self.assertEqual(res.status_code, 302)
        self.check_finished_order(cs_data['reference_number'], product.id)
