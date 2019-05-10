from decimal import Decimal
from oscar.core.loading import get_class, get_model
from oscarapicheckout.methods import PaymentMethod, PaymentMethodSerializer
from oscarapicheckout.states import FormPostRequired, Complete, Declined
from oscarapicheckout import utils
from rest_framework import serializers
from suds.sudsobject import asdict

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
    msg = 'Transaction {} is currently under review. Use Decision Manager' \
          ' to either accept or reject the transaction.'.format(transaction_id)
    create_order_note(order, msg)


def log_order_exception(order_number, order_status, reply_log_entry):
    logger.exception("Failed to set Order {} to payment declined. Order is current in status {}. "
                     "Examine CyberSourceReply[{}]").format(order_number, order_status, reply_log_entry.pk)


def mark_declined(order, request, method_key, reply_log_entry):
    amount = Decimal(request.data.get('req_amount', '0.00'))
    try:
        utils.mark_payment_method_declined(order, request, method_key, amount)
    except InvalidOrderStatus:
        log_order_exception(order.number, order.status, reply_log_entry)


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
        operation = actions.CreatePaymentToken(
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

        # Create the payment token
        if not PaymentToken.objects.filter(token=token_string).exists():
            token = PaymentToken(
                log=reply_log_entry,
                token=token_string,
                masked_card_number=card_num,
                card_type=card_type)
            token.save()


    def record_successful_authorization(self, reply_log_entry, order, data):
        """Payment Step 3: Record a successful authorization"""
        token_string = data.get('payment_token')
        transaction_id = data.get('transaction_id')
        decision = reply_log_entry.get_decision()
        request_token = data.get('request_token')
        signed_date_time = data.get('signed_date_time')
        req_amount = Decimal(data.get('req_amount', '0'))

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

        event = self.make_authorize_event(order, auth_amount, transaction_id)
        for line in order.lines.all():
            self.make_event_quantity(event, line, line.quantity)

        return Complete(source.amount_allocated, source_id=source.pk)


    def record_declined_authorization(self, reply_log_entry, order, data):
        """Payment Declined in Step 3: Record a failed authorization."""
        token_string = data.get('payment_token')
        transaction_id = data.get('transaction_id', '')
        decision = reply_log_entry.get_decision()
        request_token = data.get('request_token')
        signed_date_time = data.get('signed_date_time')
        req_amount = Decimal(data.get('req_amount', '0'))

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
            raise serializers.ValidationError('Missing encrypted payment data.')
        return super().validate(data)


class Bluefin(PaymentMethod):

    name = settings.SOURCE_TYPE
    code = 'bluefin'
    serializer_class = BluefinPaymentMethodSerializer

    @staticmethod
    def log_soap_response(request, order, response):
        # convert SOAP response to a generic python dict so it can be stored in an HStoreField
        try:
            response = asdict(response)
        except Exception:
            response = {}

        # SOAP API stores order number in merchantReferenceCode, while client-side get token uses req_reference_number
        # let's store both to make downstream code token method agnostic
        response['req_reference_number'] = response.get('merchantReferenceCode', '')

        log = CyberSourceReply(
            user=request.user if request.user.is_authenticated else None,
            order=order,
            data=response)
        log.save()
        return log

    def _record_created_payment_token(self, reply_log_entry, response):
        token_string = response.paySubscriptionCreateReply.subscriptionID
        # Create the payment token
        if not PaymentToken.objects.filter(token=token_string).exists():
            token = PaymentToken(
                log=reply_log_entry,
                token=token_string,
                masked_card_number='',
                card_type='')
            token.save()

    def _record_successful_authorization(self, reply_log_entry, order, token_string, response):
        decision = reply_log_entry.get_decision()
        transaction_id = response.encryptedPayment.referenceID
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

    def _record_declined_authorization(self, reply_log_entry, order, token_string, response):
        decision = reply_log_entry.get_decision()
        transaction_id = response.encryptedPayment.referenceID
        request_token = response.requestToken
        signed_date_time = response.ccAuthReply.authorizedDateTime
        req_amount = Decimal(response.ccAuthReply.amount)

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

        return self._record_bluefin_payment(request, order, method_key, amount, payment_data)

    def _record_bluefin_payment(self, request, order, method_key, amount, payment_data):
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

        if response.decision == DECISION_ACCEPT:
            self._record_created_payment_token(reply_log_entry, response)
            token_string = response.paySubscriptionCreateReply.subscriptionID

            # Authorize via SOAP
            response = cs.authorize_encrypted(payment_data, amount)
            reply_log_entry = self.__class__.log_soap_response(request, order, response)

            # If authorization was successful, log it and redirect to the success page.
            if response.decision in (DECISION_ACCEPT, DECISION_REVIEW):
                new_state = self._record_successful_authorization(reply_log_entry, order, token_string, response)

                if response.decision == DECISION_REVIEW:
                    create_review_order_note(order, response.encryptedPayment.referenceID)

                return new_state
            else:
                # Authorization failed
                new_state = self._record_declined_authorization(reply_log_entry, order, token_string, response)
                mark_declined(order, request, method_key, reply_log_entry)
                return new_state

        else:
            # Payment token was not created
            mark_declined(order, request, method_key, reply_log_entry)
            return Declined(amount)
