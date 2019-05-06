import logging
import soap
import uuid

from suds.sudsobject import asdict

from .constants import *

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

    def __init__(self, wsdl, merchant_id, transaction_security_key, soap_log_prefix='CYBERSOURCE'):
        self.merchant_id = merchant_id

        # Build a SOAP client
        self.client = soap.get_client(wsdl, soap_log_prefix)

        # Add WSSE Security Header to client
        security = Security()
        token = UsernameToken(self.merchant_id, transaction_security_key)
        security.tokens.append(token)
        self.client.set_options(wsse=security)

        print("init ok")

    # Authorize with a token
    def authorize(self, request, order):
        data = self.prep_transaction(request, order, 'ccAuthService')
        token_string = request.data.get('payment_token')

        # Add token info
        data['recurringSubscriptionInfo'] = self.client.factory.create('ns0:recurringSubscriptionInfo')
        data['recurringSubscriptionInfo'].subscriptionID = token_string

        return self.run_transaction(data, order)

    # Get a token using encrypted card number
    def get_token_encrypted(self, request, order, encrypted):
        data = self.prep_transaction(request, order, 'paySubscriptionCreateService')

        # Add encrypted data
        data['encryptedPayment'] = self.client.factory.create('ns0:encryptedPayment')
        data['encryptedPayment'].data = encrypted
        data['encryptedPayment'].descriptor = TERMINAL_DESCRIPTOR

        # Add token request
        data['recurringSubscriptionInfo'] = self.client.factory.create('ns0:recurringSubscriptionInfo')
        data['recurringSubscriptionInfo'].frequency = 'on-demand'

        return self.run_transaction(data, order)

    # Authorise using encrypted card number
    def authorize_encrypted(self, request, order, encrypted):
        data = self.prep_transaction(request, order, 'ccAuthService')

        # Add encrypted data
        data['encryptedPayment'] = self.client.factory.create('ns0:encryptedPayment')
        data['encryptedPayment'].data = encrypted
        data['encryptedPayment'].descriptor = TERMINAL_DESCRIPTOR

        return self.run_transaction(data, order)

    def prep_transaction(self, request, order, service):
        data = self.add_service({}, service)
        data = self.add_merchant(data, request, order)
        data = self.add_order(data, request, order)

        return data

    def add_service(self, data, service):
        data[service] = self.client.factory.create('ns0:{}'.format(service))
        data[service]._run = "true"

        return data

    def add_merchant(self, data, request, order):
        if CHECKOUT_FINGERPRINT_SESSION_ID and request.session.get(CHECKOUT_FINGERPRINT_SESSION_ID):
            data['deviceFingerprintID'] = request.session[CHECKOUT_FINGERPRINT_SESSION_ID]
        data['merchantID'] = self.merchant_id
        data['merchantReferenceCode'] = order.number

        return data

    def add_order(self, data, request, order):
        data['billTo'] = self.client.factory.create('ns0:BillTo')
        data['billTo'].email = order.email
        data['billTo'].ipAddress = request.META.get('REMOTE_ADDR')
        if order.user:
            data['billTo'].customerID = order.user.pk

        # Add order billing data
        if order.billing_address:
            data['billTo'].firstName = order.billing_address.first_name
            data['billTo'].lastName = order.billing_address.last_name
            data['billTo'].street1 = order.billing_address.line1
            data['billTo'].street2 = order.billing_address.line2
            data['billTo'].city = order.billing_address.line4
            data['billTo'].state = order.billing_address.state
            data['billTo'].postalCode = order.billing_address.postcode
            data['billTo'].country = order.billing_address.country.iso_3166_1_a2

        # Add order shipping data
        if order.shipping_address:
            data['shipTo'] = self.client.factory.create('ns0:ShipTo')
            data['shipTo'].phoneNumber = order.shipping_address.phone_number
            data['shipTo'].firstName = order.shipping_address.first_name
            data['shipTo'].lastName = order.shipping_address.last_name
            data['shipTo'].street1 = order.shipping_address.line1
            data['shipTo'].street2 = order.shipping_address.line2
            data['shipTo'].city = order.shipping_address.line4
            data['shipTo'].state = order.shipping_address.state
            data['shipTo'].postalCode = order.shipping_address.postcode
            data['shipTo'].country = order.shipping_address.country.iso_3166_1_a2

        # Add order total data
        data['purchaseTotals'] = self.client.factory.create('ns0:PurchaseTotals')
        data['purchaseTotals'].currency = order.currency

        # FIXME is this the right amount?
        # data['purchaseTotals'].grandTotalAmount = order.total_incl_tax
        data['purchaseTotals'].grandTotalAmount = request.data.get('req_amount', '0')

        return data

    def run_transaction(self, data, order):
        print(data)

        # Send the transaction to Cybersource to process
        try:
            response = self.client.service.runTransaction(**data)
        except Exception:
            logger.exception("Failed to run Cybersource SOAP transaction on Order {}".format(order.number))
            response = None

        print('----------------->')
        print(response)

        # Parse the response for a decision code and a message
        try:
            decision, message = self.parse_response_outcome(response)
        except Exception:
            decision, message = DECISION_ERROR, "Error: Could not parse Cybersource response."

        # convert response to a generic python dict so it can be stored in an HStoreField etc.
        response = asdict(response)

        return decision, message, response

    def parse_response_outcome(self, resp):
        print(resp.reasonCode)
        message = CYBERSOURCE_RESPONSES[str(resp.reasonCode)]
        if message is None:
            message = "Could not identify Cybersource response code."
        if resp.reasonCode == 100:
            decision = DECISION_ACCEPT
        elif message.startswith('Error'):
            decision = DECISION_ERROR
        else:
            decision = DECISION_DECLINE

        return decision, message
