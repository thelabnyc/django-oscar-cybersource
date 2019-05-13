import logging
import soap

from .constants import DECISION_ERROR, TERMINAL_DESCRIPTOR, CHECKOUT_FINGERPRINT_SESSION_ID
from . import signals

from suds.wsse import Security
from suds.wsse import UsernameToken

logger = logging.getLogger(__name__)


class CyberSourceSoap(object):
    """
    The given WSDL should be one of the following:

    - Test Environments: ``https://ics2wstesta.ic3.com/commerce/1.x/transactionProcessor/CyberSourceTransaction_1.141.wsdl``
    - Production Environments: ``https://ics2wsa.ic3.com/commerce/1.x/transactionProcessor/CyberSourceTransaction_1.141.wsdl``

    MerchantID should be your Cybersource account's merchant ID. Transaction security key should be a SOAP Toolkit API Security
    Keys. You can make find this in the Cybersource Business Center => Transaction Security Keys => Security Keys for the SOAP
    Toolkit API => Generate Key. It is be secret and not be checked into source-control. Treat this like a password.
    """

    def __init__(self, wsdl, merchant_id, transaction_security_key, request, order, method_key,
                 soap_log_prefix='CYBERSOURCE'):
        self.merchant_id = merchant_id
        self.request = request
        self.order = order
        self.method_key = method_key
        self.data = {}

        # Build a SOAP client
        self.client = soap.get_client(wsdl, soap_log_prefix)

        # Add WSSE Security Header to client
        security = Security()
        token = UsernameToken(self.merchant_id, transaction_security_key)
        security.tokens.append(token)
        self.client.set_options(wsse=security)

    def _get_token(self):
        return self.request.data.get('payment_token')

    def authorize(self):
        """ Authorize with a token """
        self._prep_transaction('ccAuthService')

        # Add token info
        self.data['recurringSubscriptionInfo'] = self.client.factory.create('ns0:recurringSubscriptionInfo')
        self.data['recurringSubscriptionInfo'].subscriptionID = self._get_token()

        # Add extra fields
        self._add_signal(signals.pre_build_auth_request)

        return self._run_transaction()

    def get_token_encrypted(self, encrypted):
        """ Get a token using encrypted card number """
        if encrypted is None:
            return DECISION_ERROR, None, None

        self._prep_transaction('paySubscriptionCreateService')

        # Add encrypted data
        self.data['encryptedPayment'] = self.client.factory.create('ns0:encryptedPayment')
        self.data['encryptedPayment'].data = encrypted
        self.data['encryptedPayment'].descriptor = TERMINAL_DESCRIPTOR

        # Add extra fields
        self._add_signal(signals.pre_build_get_token_request)

        # Add token request
        self.data['recurringSubscriptionInfo'] = self.client.factory.create('ns0:recurringSubscriptionInfo')
        self.data['recurringSubscriptionInfo'].frequency = 'on-demand'

        return self._run_transaction()

    def authorize_encrypted(self, encrypted, amount=None):
        """ Authorize using encrypted card number """
        if encrypted is None:
            return DECISION_ERROR, None, None

        self._prep_transaction('ccAuthService', amount)

        # Add encrypted data
        self.data['encryptedPayment'] = self.client.factory.create('ns0:encryptedPayment')
        self.data['encryptedPayment'].data = encrypted
        self.data['encryptedPayment'].descriptor = TERMINAL_DESCRIPTOR

        # Add extra fields
        self._add_signal(signals.pre_build_auth_request)

        return self._run_transaction()

    def _prep_transaction(self, service, amount=None):
        self.data = {}
        self._add_service(service)
        self._add_merchant()
        self._add_order(amount)

    def _add_service(self, service):
        self.data[service] = self.client.factory.create('ns0:{}'.format(service))
        self.data[service]._run = "true"

    def _add_merchant(self):
        if CHECKOUT_FINGERPRINT_SESSION_ID and self.request.session.get(CHECKOUT_FINGERPRINT_SESSION_ID):
            self.data['deviceFingerprintID'] = self.request.session[CHECKOUT_FINGERPRINT_SESSION_ID]
        self.data['merchantID'] = self.merchant_id
        self.data['merchantReferenceCode'] = self.order.number

    def _add_order(self, amount=None):
        self.data['billTo'] = self.client.factory.create('ns0:BillTo')
        self.data['billTo'].email = self.order.email
        self.data['billTo'].ipAddress = self.request.META.get('REMOTE_ADDR')
        if self.order.user:
            self.data['billTo'].customerID = self.order.user.pk

        # Add order billing data
        if self.order.billing_address:
            self.data['billTo'].firstName = self.order.billing_address.first_name
            self.data['billTo'].lastName = self.order.billing_address.last_name
            self.data['billTo'].street1 = self.order.billing_address.line1
            self.data['billTo'].street2 = self.order.billing_address.line2
            self.data['billTo'].city = self.order.billing_address.line4
            self.data['billTo'].state = self.order.billing_address.state
            self.data['billTo'].postalCode = self.order.billing_address.postcode
            self.data['billTo'].country = self.order.billing_address.country.iso_3166_1_a2

        # Add order shipping data
        if self.order.shipping_address:
            self.data['shipTo'] = self.client.factory.create('ns0:ShipTo')
            self.data['shipTo'].phoneNumber = self.order.shipping_address.phone_number
            self.data['shipTo'].firstName = self.order.shipping_address.first_name
            self.data['shipTo'].lastName = self.order.shipping_address.last_name
            self.data['shipTo'].street1 = self.order.shipping_address.line1
            self.data['shipTo'].street2 = self.order.shipping_address.line2
            self.data['shipTo'].city = self.order.shipping_address.line4
            self.data['shipTo'].state = self.order.shipping_address.state
            self.data['shipTo'].postalCode = self.order.shipping_address.postcode
            self.data['shipTo'].country = self.order.shipping_address.country.iso_3166_1_a2

        # Add order total data
        self.data['purchaseTotals'] = self.client.factory.create('ns0:PurchaseTotals')
        self.data['purchaseTotals'].currency = self.order.currency
        self.data['purchaseTotals'].grandTotalAmount = amount if amount is not None \
            else self.request.data.get('req_amount', '0')

    def _add_signal(self, signal):
        extra_fields = {}
        signal.send(
            sender=self.__class__,
            extra_fields=extra_fields,
            request=self.request,
            order=self.order,
            token=self._get_token(),
            method_key=self.method_key)

        self.data['merchantDefinedData'] = self.client.factory.create('ns0:MerchantDefinedData')

        # TODO would be nice if `merchant_defined_dataX` wasn't hardcoded
        i = 1
        while 'merchant_defined_data{}'.format(i) in extra_fields:
            self.data['merchantDefinedData']['field{}'.format(i)] = extra_fields['merchant_defined_data{}'.format(i)]
            i += 1

    def _run_transaction(self):

        # Send the transaction to Cybersource to process
        try:
            response = self.client.service.runTransaction(**self.data)
        except Exception:
            logger.exception("Failed to run Cybersource SOAP transaction on Order {}".format(self.order.number))
            response = None


        return response
