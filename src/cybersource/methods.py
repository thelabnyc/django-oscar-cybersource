from decimal import Decimal
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.conf import settings as django_settings
from oscar.core.loading import get_class, get_model
from oscarapicheckout.methods import PaymentMethod, PaymentMethodSerializer
from oscarapicheckout.states import FormPostRequired, Complete, Declined
from oscarapicheckout import utils
from rest_framework import serializers
from suds import sudsobject
from cybersource.cybersoap import CyberSourceSoap
from .constants import CHECKOUT_FINGERPRINT_SESSION_ID, DECISION_ACCEPT, DECISION_REVIEW
from .models import PaymentToken, CyberSourceReply
from . import actions, signals, settings
import dateutil.parser
import logging

logger = logging.getLogger(__name__)

Transaction = get_model('payment', 'Transaction')
InvalidOrderStatus = get_class('order.exceptions', 'InvalidOrderStatus')
OrderNote = get_model('order', 'OrderNote')


def create_order_note(order, msg):
    return OrderNote.objects.create(
        note_type=OrderNote.SYSTEM,
        order=order,
        message=msg)


def create_review_order_note(order, transaction_id):
    """ If an order is under review, add a note explaining why"""
    msg = _('Transaction %(transaction_id)s is currently under review. Use Decision Manager to either accept or reject the transaction.') % dict(
        transaction_id=transaction_id)
    create_order_note(order, msg)


def log_order_exception(order_number, order_status, reply_log_entry):
    logger.exception(
        "Failed to set Order %s to payment declined. Order is current in status %s. Examine CyberSourceReply[%s]",
        order_number, order_status, reply_log_entry.pk)


def mark_declined(order, request, method_key, reply_log_entry):
    amount = Decimal(request.data.get('req_amount', '0.00'))
    try:
        utils.mark_payment_method_declined(order, request, method_key, amount)
    except InvalidOrderStatus:
        log_order_exception(order.number, order.status, reply_log_entry)


def sudsobj_to_dict(sudsobj, key_prefix=''):
    """Convert Suds object into a flattened dictionary"""
    out = {}
    # Handle lists
    if isinstance(sudsobj, list):
        for i, child in enumerate(sudsobj):
            child_key = '{}[{}]'.format(key_prefix, i)
            out.update(sudsobj_to_dict(child, key_prefix=child_key))
        return out
    # Handle Primitives
    if not hasattr(sudsobj, '__keylist__'):
        out[key_prefix] = sudsobj
        return out
    # Handle Suds Objects
    for parent_key, parent_val in sudsobject.asdict(sudsobj).items():
        full_parent_key = '{}.{}'.format(key_prefix, parent_key) if key_prefix else parent_key
        out.update(sudsobj_to_dict(parent_val, key_prefix=full_parent_key))
    return out



class Cybersource(PaymentMethod):
    """
    This is an example of how to implement a payment method that required some off-site
    interaction, like Cybersource Secure Acceptance, for example. It returns a pending
    status initially that requires the client app to make a form post, which in-turn
    redirects back to us. This is a common pattern in PCI SAQ A-EP ecommerce sites.
    """
    name = settings.SOURCE_TYPE
    code = 'cybersource'
    serializer_class = PaymentMethodSerializer


    def _record_payment(self, request, order, method_key, amount, reference, **kwargs):
        """Payment Step 1: Require form POST to Cybersource"""
        # Allow application to include extra, arbitrary fields in the request to CS
        extra_fields = {}
        signals.pre_build_get_token_request.send(
            sender=self.__class__,
            extra_fields=extra_fields,
            request=request,
            order=order,
            method_key=method_key)

        # Build the data for CyberSource transaction
        session_id = request.COOKIES.get(django_settings.SESSION_COOKIE_NAME)
        operation = actions.CreatePaymentToken(
            session_id=session_id,
            order=order,
            method_key=method_key,
            amount=amount,
            server_hostname=request.META.get('HTTP_HOST', ''),
            customer_ip_address=request.META['REMOTE_ADDR'],
            fingerprint_session_id=request.session.get(CHECKOUT_FINGERPRINT_SESSION_ID),
            extra_fields=extra_fields)

        # Return form fields to the browser. The browser then needs to fill in the blank
        # fields (like billing data) and submit them as a POST to CyberSource.
        url, fields = self._fields(operation)

        # Return a response showing we need to post some fields to the given
        # URL to finishing processing this payment method
        return FormPostRequired(
            amount=amount,
            name='get-token',
            url=url,
            fields=fields)


    def record_created_payment_token(self, reply_log_entry, data):
        """Payment Step 2: Record the generated payment token and require authorization using the token."""
        token_string = data.get('payment_token')
        card_num = data.get('req_card_number')
        card_type = data.get('req_card_type')
        try:
            token = PaymentToken.objects.filter(token=token_string).get()
        except PaymentToken.DoesNotExist:
            token = PaymentToken(
                log=reply_log_entry,
                token=token_string,
                masked_card_number=card_num,
                card_type=card_type)
            token.save()
        return token, None


    def _fields(self, operation):
        """Helper to convert an operation object into a list of fields and a URL"""
        fields = []
        cs_fields = operation.fields()
        editable_fields = cs_fields['unsigned_field_names'].split(',')
        for key, value in cs_fields.items():
            fields.append({
                'key': key,
                'value': value if isinstance(value, str) else value.decode(),
                'editable': (key in editable_fields)
            })

        return operation.url, fields



class BluefinPaymentMethodSerializer(PaymentMethodSerializer):
    payment_data = serializers.CharField(max_length=256)

    def validate(self, data):
        if 'payment_data' not in data:
            raise serializers.ValidationError(_('Missing encrypted payment data.'))
        return super().validate(data)



class Bluefin(PaymentMethod):
    name = settings.SOURCE_TYPE
    code = 'bluefin'
    serializer_class = BluefinPaymentMethodSerializer

    @staticmethod
    def log_soap_response(request, order, response, card_expiry_date=None):
        reply_data = sudsobj_to_dict(response)
        log = CyberSourceReply(
            user=request.user if request.user.is_authenticated else None,
            order=order,
            reply_type=CyberSourceReply.REPLY_TYPE_SOAP,
            data=reply_data,
            decision=response.decision,
            message=None,
            reason_code=response.reasonCode,
            req_bill_to_address_postal_code=order.billing_address.postcode,
            req_bill_to_forename=order.billing_address.first_name,
            req_bill_to_surname=order.billing_address.last_name,
            req_card_expiry_date=card_expiry_date,
            req_reference_number=response.merchantReferenceCode if 'merchantReferenceCode' in response else None,
            req_transaction_type=('create_payment_token' if 'paySubscriptionCreateReply' in response else 'authorization'),
            req_transaction_uuid=None,
            request_token=response.requestToken,
            transaction_id=response.requestID,
        )
        # These fields may or may not be present
        cc_auth_reply = getattr(response, 'ccAuthReply', None)
        if cc_auth_reply:
            log.auth_code = getattr(cc_auth_reply, 'authorizationCode', None)
            log.auth_response = getattr(cc_auth_reply, 'processorResponse', None)
            log.auth_trans_ref_no = getattr(cc_auth_reply, 'reconciliationID', None)
            log.auth_avs_code = getattr(cc_auth_reply, 'avsCode', None)
        # Save and return log object
        log.save()
        return log


    @staticmethod
    def lookup_token_details(request, order, payment_token):
        cs = CyberSourceSoap(
            settings.CYBERSOURCE_WSDL,
            settings.MERCHANT_ID,
            settings.CYBERSOURCE_SOAP_KEY,
            request,
            order,
            '')
        return cs.lookup_payment_token(payment_token)


    def record_created_payment_token(self, request, order, reply_log_entry, response):
        token_string = response.paySubscriptionCreateReply.subscriptionID
        # Lookup more details about the token
        token_details = self.__class__.lookup_token_details(request, order, token_string)
        # Create the payment token
        if not PaymentToken.objects.filter(token=token_string).exists():
            token = PaymentToken(
                log=reply_log_entry,
                token=token_string,
                masked_card_number=token_details.paySubscriptionRetrieveReply.cardAccountNumber,
                card_type=token_details.paySubscriptionRetrieveReply.cardType)
            token.save()
        return token, token_details


    def record_successful_authorization(self, reply_log_entry, order, token_string, response):
        decision = reply_log_entry.get_decision()
        transaction_id = response.requestID
        request_token = response.requestToken
        signed_date_time = response.ccAuthReply.authorizedDateTime
        req_amount = Decimal(response.ccAuthReply.amount)

        # assuming these are equal since authorization succeeded
        auth_amount = req_amount

        source = self.get_source(order, transaction_id)

        try:
            token = PaymentToken.objects.get(token=token_string)
        except PaymentToken.DoesNotExist:
            return Declined(req_amount, source_id=source.pk)

        source.amount_allocated += auth_amount
        source.save()
        transaction = Transaction()
        transaction.log = reply_log_entry
        transaction.source = source
        transaction.token = token
        transaction.txn_type = Transaction.AUTHORISE
        transaction.amount = req_amount
        transaction.reference = transaction_id
        transaction.status = decision
        transaction.request_token = request_token
        transaction.processed_datetime = dateutil.parser.parse(signed_date_time)
        transaction.save()
        event = self.make_authorize_event(order, auth_amount)
        for line in order.lines.all():
            self.make_event_quantity(event, line, line.quantity)
        return Complete(source.amount_allocated, source_id=source.pk)


    def record_declined_authorization(self, reply_log_entry, order, token_string, response, amount):
        decision = reply_log_entry.get_decision()
        transaction_id = response.requestID
        request_token = response.requestToken
        signed_date_time = str(timezone.now())  # not available in response.ccAuthReply
        req_amount = amount  # not available in response.ccAuthReply

        source = self.get_source(order, transaction_id)

        transaction = Transaction()
        transaction.log = reply_log_entry
        transaction.source = source
        transaction.token = PaymentToken.objects.filter(token=token_string).first()
        transaction.txn_type = Transaction.AUTHORISE
        transaction.amount = req_amount
        transaction.reference = transaction_id
        transaction.status = decision
        transaction.request_token = request_token
        transaction.processed_datetime = dateutil.parser.parse(signed_date_time)
        transaction.save()

        return Declined(req_amount, source_id=source.pk)


    def _record_payment(self, request, order, method_key, amount, reference, **kwargs):
        """ This is the entry point from django-oscar-api-checkout """
        payment_data = kwargs.get('payment_data')
        if payment_data is None:
            return Declined(amount)
        return self.record_bluefin_payment(request, order, method_key, amount, payment_data)


    def record_bluefin_payment(self, request, order, method_key, amount, payment_data):
        # Allow application to include extra, arbitrary fields in the request to CS
        extra_fields = {}
        signals.pre_build_get_token_request.send(
            sender=self.__class__,
            extra_fields=extra_fields,
            request=request,
            order=order,
            method_key=method_key)

        cs = CyberSourceSoap(
            settings.CYBERSOURCE_WSDL,
            settings.MERCHANT_ID,
            settings.CYBERSOURCE_SOAP_KEY,
            request,
            order,
            method_key)

        # Get token via SOAP
        response = cs.get_token_encrypted(payment_data)
        reply_log_entry = self.__class__.log_soap_response(request, order, response)

        # If token creation was not successful, return declined.
        if response.decision != DECISION_ACCEPT:
            return Declined(amount)

        # Record the new payment token
        token, token_details = self.record_created_payment_token(request, order, reply_log_entry, response)
        expiry_date = "{month}-{year}".format(
            month=token_details.paySubscriptionRetrieveReply.cardExpirationMonth,
            year=token_details.paySubscriptionRetrieveReply.cardExpirationYear)
        reply_log_entry.req_card_expiry_date = expiry_date
        reply_log_entry.save()

        # Attempt to authorize payment
        response = cs.authorize_encrypted(payment_data, amount)
        reply_log_entry = self.__class__.log_soap_response(request, order, response,
            card_expiry_date=expiry_date)

        # If authorization was not successful, log it and redirect to the failed page.
        if response.decision not in (DECISION_ACCEPT, DECISION_REVIEW):
            new_state = self.record_declined_authorization(reply_log_entry, order, token.token, response, amount)
            return new_state

        # Authorization was successful! Log it and update he order state
        new_state = self.record_successful_authorization(reply_log_entry, order, token.token, response)
        if response.decision == DECISION_REVIEW:
            create_review_order_note(order, response.requestID)
        return new_state
