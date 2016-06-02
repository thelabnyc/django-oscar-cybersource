from datetime import datetime
from . import settings, signature
import random
import time
import re


class SecureAcceptanceAction(object):
    access_key = settings.ACCESS
    currency = settings.DEFAULT_CURRENCY
    date_format = settings.DATE_FORMAT
    locale = settings.LOCALE
    profile_id = settings.PROFILE
    signed_field_names = set()
    transaction_type = ''
    unsigned_field_names = set()


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

        signer = signature.SecureAcceptanceSigner()
        fields['signature'] = signer.sign(fields, signed_fields)
        return fields

    def build_request_data(self):
        data = {
            'access_key': self.access_key,
            'currency': self.currency,
            'locale': self.locale,
            'profile_id': self.profile_id,
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


class CreateAndAuthorizePaymentToken(SecureAcceptanceAction):
    signed_field_names = set([
        'access_key',
        'profile_id',
        'transaction_uuid',
        'signed_field_names',
        'unsigned_field_names',
        'signed_date_time',
        'locale',
        'transaction_type',
        'reference_number',
        'customer_ip_address',
        'device_fingerprint_id',
        'payment_method',
        'ship_to_forename',
        'ship_to_surname',
        'ship_to_address_line1',
        'ship_to_address_line2',
        'ship_to_address_city',
        'ship_to_address_state',
        'ship_to_address_country',
        'ship_to_address_postal_code',
        'ship_to_phone',
        'currency',
        'amount',
        'line_item_count',
    ])
    unsigned_field_names = set([
        'bill_to_forename',
        'bill_to_surname',
        'bill_to_address_line1',
        'bill_to_address_line2',
        'bill_to_address_city',
        'bill_to_address_state',
        'bill_to_address_postal_code',
        'bill_to_address_country',
        'bill_to_phone',
        'bill_to_email',
        'card_type',
        'card_number',
        'card_expiry_date',
        'card_cvn',
    ])
    transaction_type = 'authorization,create_payment_token'
    url = settings.ENDPOINT_PAY


    def __init__(self, order, amount, **kwargs):
        self.order = order
        self.amount = amount
        self.customer_ip_address = kwargs.get('customer_ip_address')
        self.device_fingerprint_id = kwargs.get('fingerprint_session_id')
        self.extra_fields = kwargs.get('extra_fields')


    def build_signed_data(self):
        data = {}

        # Basic order info
        data['payment_method'] = 'card'
        data['reference_number'] = str(self.order.number)
        data['currency'] = self.order.currency
        data['amount'] = str(self.amount)

        # Add shipping and billing info
        if self.order.shipping_address:
            data['ship_to_forename'] = self.order.shipping_address.first_name
            data['ship_to_surname'] = self.order.shipping_address.last_name
            data['ship_to_address_line1'] = self.order.shipping_address.line1
            data['ship_to_address_line2'] = self.order.shipping_address.line2
            data['ship_to_address_city'] = self.order.shipping_address.line4
            data['ship_to_address_state'] = self.order.shipping_address.state
            data['ship_to_address_postal_code'] = self.order.shipping_address.postcode
            data['ship_to_phone'] = re.sub('[^0-9]', '', self.order.shipping_address.phone_number.as_rfc3966)
            data['ship_to_address_country'] = self.order.shipping_address.country.code

        if self.order.billing_address:
            data['bill_to_forename'] = self.order.billing_address.first_name
            data['bill_to_surname'] = self.order.billing_address.last_name
            data['bill_to_address_line1'] = self.order.billing_address.line1
            data['bill_to_address_line2'] = self.order.billing_address.line2
            data['bill_to_address_city'] = self.order.billing_address.line4
            data['bill_to_address_state'] = self.order.billing_address.state
            data['bill_to_address_postal_code'] = self.order.billing_address.postcode
            data['bill_to_address_country'] = self.order.billing_address.country.code

        # Add line item info
        i = 0
        for line in self.order.lines.all():
            data['item_%s_name' % i] = line.product.title
            data['item_%s_sku' % i] = line.partner_sku
            data['item_%s_quantity' % i] = str(line.quantity)
            data['item_%s_unit_price' % i] = str(line.unit_price_incl_tax)
            i += 1
        data['line_item_count'] = str(i)

        # Other misc fields
        for field in ('customer_ip_address', 'device_fingerprint_id'):
            value = getattr(self, field, None)
            if value is not None:
                data[field] = value
        data.update(self.extra_fields)

        return data
