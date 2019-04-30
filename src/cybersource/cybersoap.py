import logging
import soap
import uuid

from suds.wsse import Security
from suds.wsse import UsernameToken

logger = logging.getLogger(__name__)

CHECKOUT_ORDER_ID = 'checkout_order_id'
CHECKOUT_FINGERPRINT_SESSION_ID = 'cybersource_fingerprint_session_id'

DECISION_ACCEPT = 'ACCEPT'
DECISION_REVIEW = 'REVIEW'
DECISION_DECLINE = 'DECLINE'
DECISION_ERROR = 'ERROR'

TERMINAL_DESCRIPTOR = 'Ymx1ZWZpbg=='

# noqa: E501
CYBERSOURCE_RESPONSES = {
    '100': 'Successful transaction.',
    '101': 'The request is missing one or more required fields.',
    '102': 'One or more fields in the request contains invalid data.',
    '104': 'The merchantReferenceCode sent with this authorization request matches the merchantReferenceCode of another authorization request that you sent in the last 15 minutes.',
    '150': 'Error: General system failure. ',
    '151': 'Error: The request was received but there was a server timeout. This error does not include timeouts between the client and the server.',
    '152': 'Error: The request was received, but a service did not finish running in time.',
    '201': 'The issuing bank has questions about the request. You do not receive an authorization code in the reply message, but you might receive one verbally by calling the processor.',
    '202': 'Expired card. You might also receive this if the expiration date you provided does not match the date the issuing bank has on file.',
    '203': 'General decline of the card. No other information provided by the issuing bank.',
    '204': 'Insufficient funds in the account.',
    '205': 'Stolen or lost card.',
    '207': 'Issuing bank unavailable.',
    '208': 'Inactive card or card not authorized for card-not-present transactions.',
    '210': 'The card has reached the credit limit. ',
    '211': 'Invalid card verification number.',
    '221': 'The customer matched an entry on the processor\'s negative file.',
    '231': 'Invalid account number.',
    '232': 'The card type is not accepted by the payment processor.',
    '233': 'General decline by the processor.',
    '234': 'There is a problem with your CyberSource merchant configuration.',
    '235': 'The requested amount exceeds the originally authorized amount. Occurs, for example, if you try to capture an amount larger than the original authorization amount. This reason code only applies if you are processing a capture through the API.',
    '236': 'Processor Failure',
    '238': 'The authorization has already been captured. This reason code only applies if you are processing a capture through the API.',
    '239': 'The requested transaction amount must match the previous transaction amount. This reason code only applies if you are processing a capture or credit through the API.',
    '240': 'The card type sent is invalid or does not correlate with the credit card number.',
    '241': 'The request ID is invalid. This reason code only applies when you are processing a capture or credit through the API.',
    '242': 'You requested a capture through the API, but there is no corresponding, unused authorization record. Occurs if there was not a previously successful authorization request or if the previously successful authorization has already been used by another capture request. This reason code only applies when you are processing a capture through the API.',
    '243': 'The transaction has already been settled or reversed.',
    '246': 'The capture or credit is not voidable because the capture or credit information has already been submitted to your processor. Or, you requested a void for a type of transaction that cannot be voided. This reason code applies only if you are processing a void through the API.',
    '247': 'You requested a credit for a capture that was previously voided. This reason code applies only if you are processing a void through the API.',
    '250': 'Error: The request was received, but there was a timeout at the payment processor.',
    '520': 'The authorization request was approved by the issuing bank but declined by CyberSource based on your Smart Authorization settings.',
}


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

    # we probably don't need this and can just authorize and hopefully get back a token
    def get_token_encrypted(self, request, order, data):
        data = self.prep_transaction(request, order, 'paySubscriptionCreateService')

        # Add encrypted data
        data['encryptedPayment'] = self.client.factory.create('ns0:encryptedPayment')
        data['encryptedPayment'].data = '02A600C0170018008292;4111********1111=1912?*6D929248974C89EDD6C6079A89BC80D2F0F9AE888BFB2A5A000000000000000000000000000000000000000038343355313138373932629949960E004A800003103803'
        data['encryptedPayment'].descriptor = TERMINAL_DESCRIPTOR

        return self.run_transaction(data, order)

    def authorize_encrypted(self, request, order, data):
        data = self.prep_transaction(request, order, 'ccAuthService')

        # Add encrypted data
        data['encryptedPayment'] = self.client.factory.create('ns0:encryptedPayment')
        data['encryptedPayment'].data = '02A600C0170018008292;4111********1111=1912?*6D929248974C89EDD6C6079A89BC80D2F0F9AE888BFB2A5A000000000000000000000000000000000000000038343355313138373932629949960E004A800003103803'
        data['encryptedPayment'].descriptor = TERMINAL_DESCRIPTOR

        return self.run_transaction(data, order)

    def prep_transaction(self, request, order, service):
        data = self.add_service({}, service)
        data = self.add_merchant(data, request, order)
        data = self.add_order(data, request, order)

        return data

    def add_service(self, data, service):
        data[service] = self.client.factory.create('ns0:{}}'.format(service))
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
        data['purchaseTotals'].grandTotalAmount = order.total_incl_tax

        return data

    def run_transaction(self, data, order):
        print(data)

        # Send the transaction to Cybersource to process
        try:
            resp = self.client.service.runTransaction(**data)
        except Exception:
            logger.exception("Failed to run Cybersource SOAP transaction on Order {}".format(order.number))
            resp = None

        # Parse the response for a decision code and a message
        decision, message = self.parse_response_outcome(resp)

        # Get the transaction ID
        try:
            reference = resp.requestID
        except Exception:
            reference = uuid.uuid1()

        return decision, message, reference

    def parse_response_outcome(self, resp):
        message = CYBERSOURCE_RESPONSES[resp.reasonCode]
        if message is None:
            message = "Error: Could not parse Cybersource response."
        if resp.reasonCode == 100:
            decision = DECISION_ACCEPT
        elif message.startswith('Error'):
            decision = DECISION_ERROR
        else:
            decision = DECISION_DECLINE

        return decision, message
