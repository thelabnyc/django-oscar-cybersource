from datetime import datetime
from decimal import Decimal
from oscar.core.loading import get_model
from oscarapicheckout.methods import PaymentMethod, PaymentMethodSerializer
from oscarapicheckout.states import FormPostRequired, Complete, Declined
from .constants import CHECKOUT_FINGERPRINT_SESSION_ID
from .models import PaymentToken
from . import actions, signals, settings

Transaction = get_model('payment', 'Transaction')


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


    # Payment Step 1: Require form POST to Cybersource
    def _record_payment(self, request, order, amount, reference, **kwargs):
        source = self.get_source(order, reference)
        amount_to_allocate = amount - source.amount_allocated

        # Allow application to include extra, arbitrary fields in the request to CS
        extra_fields = {}
        signals.pre_build_get_token_request.send(
            sender=self.__class__,
            extra_fields=extra_fields,
            request=request,
            order=order,
            source=source)

        # Build the data for CyberSource transaction
        operation = actions.CreatePaymentToken(
            order=order,
            amount=amount_to_allocate,
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


    # Payment Step 2: Record the generated payment token and require authorization using the token.
    def record_created_payment_token(self, request, reply_log_entry, order, data):
        token_string = data.get('payment_token')
        card_num = data.get('req_card_number')
        card_type = data.get('req_card_type')
        req_amount = Decimal(data.get('req_amount', '0'))

        # Create the payment token
        try:
            token = PaymentToken.objects.get(token=token_string)
        except PaymentToken.DoesNotExist:
            token = PaymentToken(
                log=reply_log_entry,
                token=token_string,
                masked_card_number=card_num,
                card_type=card_type)
            token.save()

        # Allow application to include extra, arbitrary fields in the request to CS
        extra_fields = {}
        signals.pre_build_auth_request.send(
            sender=self.__class__,
            extra_fields=extra_fields,
            request=request,
            order=order,
            token=token)

        # Build the data for CyberSource transaction
        operation = actions.AuthorizePaymentToken(
            token_string=token_string,
            order=order,
            amount=req_amount,
            customer_ip_address=request.META['REMOTE_ADDR'],
            fingerprint_session_id=request.session.get(CHECKOUT_FINGERPRINT_SESSION_ID),
            extra_fields=extra_fields)

        # Return form fields to the browser. The browser then needs to fill in the blank
        # fields (like billing data) and submit them as a POST to CyberSource.
        url, fields = self._fields(operation)

        # Require that the client now perform an authorization using this token
        return FormPostRequired(
            amount=req_amount,
            name='authorize',
            url=url,
            fields=fields)


    # Payment Step 3: Record a successful authorization
    def record_successful_authorization(self, reply_log_entry, order, data):
        token_string = data.get('req_payment_token')
        transaction_id = data.get('transaction_id')
        decision = data.get('decision')
        request_token = data.get('request_token')
        signed_date_time = data.get('signed_date_time')
        auth_amount = Decimal(data.get('auth_amount', '0'))
        req_amount = Decimal(data.get('req_amount', '0'))

        try:
            token = PaymentToken.objects.get(token=token_string)
        except PaymentToken.DoesNotExist:
            return Declined(req_amount)

        source = self.get_source(order, transaction_id)
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
        transaction.processed_datetime = datetime.strptime(signed_date_time, settings.DATE_FORMAT)
        transaction.save()

        event = self.make_authorize_event(order, auth_amount, transaction_id)
        for line in order.lines.all():
            self.make_event_quantity(event, line, line.quantity)

        return Complete(source.amount_allocated)


    # Payment Declined in Step 3: Record a failed authorization.
    def record_declined_authorization(self, reply_log_entry, order, data):
        token_string = data.get('req_payment_token')
        transaction_id = data.get('transaction_id', '')
        decision = data.get('decision')
        request_token = data.get('request_token')
        signed_date_time = data.get('signed_date_time')
        req_amount = Decimal(data.get('req_amount', '0'))

        transaction = Transaction()
        transaction.log = reply_log_entry
        transaction.source = self.get_source(order, transaction_id)
        transaction.token = PaymentToken.objects.filter(token=token_string).first()
        transaction.txn_type = Transaction.AUTHORISE
        transaction.amount = req_amount
        transaction.reference = transaction_id
        transaction.status = decision
        transaction.request_token = request_token
        transaction.processed_datetime = datetime.strptime(signed_date_time, settings.DATE_FORMAT)
        transaction.save()

        return Declined(req_amount)


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
