from decimal import Decimal
from datetime import datetime
from . import settings, signature, models
import random
import time
import re

PRECISION = Decimal('0.01')


class SecureAcceptanceAction(object):
    currency = settings.DEFAULT_CURRENCY
    date_format = settings.DATE_FORMAT
    locale = settings.LOCALE
    transaction_type = ''


    def __init__(self, server_hostname):
        self.profile = models.SecureAcceptanceProfile.get_profile(server_hostname)


    @property
    def signed_field_names(self):
        return set([
            'access_key',
            'profile_id',
            'transaction_uuid',
            'signed_field_names',
            'unsigned_field_names',
            'signed_date_time',
            'locale',
            'transaction_type',
        ])


    @property
    def unsigned_field_names(self):
        return set([])


    def fields(self):
        names = self.signed_field_names | self.unsigned_field_names
        fields = { name: '' for name in names }

        data, signed_fields = self.build_request_data()
        fields.update(data)

        signed_fields = signed_fields | set(['signed_date_time', 'signed_field_names', 'unsigned_field_names'])
        unsigned_fields = set(fields.keys()) - signed_fields
        fields['signed_date_time'] = datetime.utcnow().strftime(self.date_format)
        fields['signed_field_names'] = ','.join(signed_fields)
        fields['unsigned_field_names'] = ','.join(unsigned_fields)

        signer = signature.SecureAcceptanceSigner(self.profile.secret_key)
        fields['signature'] = signer.sign(fields, signed_fields)
        return fields

    def build_request_data(self):
        data = {
            'access_key': self.profile.access_key,
            'currency': self.currency,
            'locale': self.locale,
            'profile_id': self.profile.profile_id,
            'transaction_type': self.transaction_type,
            'transaction_uuid': self.generate_uuid(),
        }

        data.update( self.build_signed_data() )
        signed_fields = self.signed_field_names | set(data.keys())
        data.update( self.build_unsigned_data() )
        return data, signed_fields


    def build_signed_data(self):
        return {}

    def build_unsigned_data(self):
        return {}

    def generate_uuid(self):
        return '%s%s' % (int(time.time()), random.randrange(0, 100))



class ShippingAddressMixin(object):
    def _get_shipping_signed_fields(self):
        return set([
            'ship_to_forename',
            'ship_to_surname',
            'ship_to_address_line1',
            'ship_to_address_line2',
            'ship_to_address_city',
            'ship_to_address_state',
            'ship_to_address_postal_code',
            'ship_to_address_country',
            'ship_to_phone',
            'shipping_method'
        ])

    def _get_shipping_unsigned_fields(self):
        return set([])


    def _get_shipping_data(self):
        order_shipping_code = str(self.order.shipping_code)
        cs_shipping_code = settings.SHIPPING_METHOD_MAPPING.get(order_shipping_code, settings.SHIPPING_METHOD_DEFAULT)
        shipping_data = {
            'shipping_method': cs_shipping_code
        }

        if self.order.shipping_address:
            shipping_data['ship_to_forename'] = self.order.shipping_address.first_name
            shipping_data['ship_to_surname'] = self.order.shipping_address.last_name
            shipping_data['ship_to_address_line1'] = self.order.shipping_address.line1
            shipping_data['ship_to_address_line2'] = self.order.shipping_address.line2
            shipping_data['ship_to_address_city'] = self.order.shipping_address.line4
            shipping_data['ship_to_address_state'] = self.order.shipping_address.state
            shipping_data['ship_to_address_postal_code'] = self.order.shipping_address.postcode
            shipping_data['ship_to_address_country'] = self.order.shipping_address.country.code
            shipping_data['ship_to_phone'] = re.sub('[^0-9]', '', self.order.shipping_address.phone_number.as_rfc3966)

        return shipping_data


class BillingAddressMixin(object):
    def _get_billing_signed_fields(self):
        return set([
            'bill_to_forename',
            'bill_to_surname',
            'bill_to_address_line1',
            'bill_to_address_line2',
            'bill_to_address_city',
            'bill_to_address_state',
            'bill_to_address_postal_code',
            'bill_to_address_country',
            'bill_to_email',
        ])

    def _get_billing_unsigned_fields(self):
        return set([
            # Oscar doesn't track phone number for billing addresses. Set this as unsigned to that the client JS can specify it if they want.
            'bill_to_phone',
        ])

    def _get_billing_data(self):
        data = {
            'bill_to_email': self.order.email,
        }
        if self.order.billing_address:
            data['bill_to_forename'] = self.order.billing_address.first_name
            data['bill_to_surname'] = self.order.billing_address.last_name
            data['bill_to_address_line1'] = self.order.billing_address.line1
            data['bill_to_address_line2'] = self.order.billing_address.line2
            data['bill_to_address_city'] = self.order.billing_address.line4
            data['bill_to_address_state'] = self.order.billing_address.state
            data['bill_to_address_postal_code'] = self.order.billing_address.postcode
            data['bill_to_address_country'] = self.order.billing_address.country.code
        return data


class OrderAction(SecureAcceptanceAction, ShippingAddressMixin, BillingAddressMixin):
    method_key_field_name = 'merchant_defined_data50'

    """
    Abstract SecureAcceptanceAction for action's related to orders.
    """
    def __init__(self, order, method_key, amount, server_hostname, **kwargs):
        self.order = order
        self.method_key = method_key
        self.amount = amount
        self.customer_ip_address = kwargs.get('customer_ip_address')
        self.device_fingerprint_id = kwargs.get('fingerprint_session_id')
        self.extra_fields = kwargs.get('extra_fields')
        super().__init__(server_hostname)


    @property
    def signed_field_names(self):
        fields = super().signed_field_names
        fields = fields | self._get_shipping_signed_fields()
        fields = fields | self._get_billing_signed_fields()
        fields = fields | set([
            'payment_method',
            'reference_number',
            'currency',
            'amount',
            'line_item_count',
            'customer_ip_address',
            'device_fingerprint_id',
            self.method_key_field_name,
        ])
        return fields


    @property
    def unsigned_field_names(self):
        fields = super().unsigned_field_names
        fields = fields | self._get_shipping_unsigned_fields()
        fields = fields | self._get_billing_unsigned_fields()
        return fields


    def build_signed_data(self):
        data = {}

        # Basic order info
        data['payment_method'] = 'card'
        data['reference_number'] = str(self.order.number)
        data['currency'] = self.order.currency
        data[self.method_key_field_name] = self.method_key
        data['amount'] = str(self.amount.quantize(PRECISION))

        # Add shipping and billing info
        data.update(self._get_shipping_data())
        data.update(self._get_billing_data())

        # Add line item info
        i = 0
        for line in self.order.lines.all():
            data['item_%s_name' % i] = line.product.title
            data['item_%s_sku' % i] = line.partner_sku
            data['item_%s_quantity' % i] = str(line.quantity)
            data['item_%s_unit_price' % i] = str(line.unit_price_incl_tax.quantize(PRECISION))
            i += 1
        data['line_item_count'] = str(i)

        # Other misc fields
        for field in ('customer_ip_address', 'device_fingerprint_id'):
            value = getattr(self, field, None)
            if value is not None:
                data[field] = value
        data.update(self.extra_fields)

        return data


class CreatePaymentToken(OrderAction):
    transaction_type = 'create_payment_token'
    url = settings.ENDPOINT_PAY

    @property
    def unsigned_field_names(self):
        fields = super().unsigned_field_names
        fields = fields | set([
            # There are unsigned as the server should *never* know them. The client JS must fill them in.
            'card_type',
            'card_number',
            'card_expiry_date',
            'card_cvn',
        ])
        return fields


class AuthorizePaymentToken(OrderAction):
    transaction_type = 'authorization'
    url = settings.ENDPOINT_PAY

    def __init__(self, token_string, order, method_key, amount, server_hostname, **kwargs):
        self.token_string = token_string
        super().__init__(order, method_key, amount, server_hostname, **kwargs)


    @property
    def signed_field_names(self):
        fields = super().signed_field_names
        fields = fields | set([
            'payment_token',
        ])
        return fields


    def build_signed_data(self):
        data = super().build_signed_data()
        data['payment_token'] = self.token_string
        return data
