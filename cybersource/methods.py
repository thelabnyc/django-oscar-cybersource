from datetime import datetime
from decimal import Decimal
from oscar.core.loading import get_model
from oscarapicheckout.methods import PaymentMethod, PaymentMethodSerializer
from oscarapicheckout.states import FormPostRequired, Complete
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
    name = 'Cybersource Secure Acceptance'
    code = 'cybersource'
    serializer_class = PaymentMethodSerializer


    # Payment Step 1: Require form POST to Cybersource
    def _record_payment(self, request, order, amount, reference, **kwargs):
        source = self.get_source(order, reference)
        amount_to_allocate = amount - source.amount_allocated

        # Allow application to include extra, arbitrary fields in the request to CS
        extra_fields = { 'bill_to_email': order.email }
        signals.pre_build_auth_request.send(
            sender=self.__class__,
            extra_fields=extra_fields,
            request=request,
            order=order)

        # Build the data for CyberSource transaction
        operation = actions.CreateAndAuthorizePaymentToken(**{
            'order': order,
            'amount': amount_to_allocate,
            'customer_ip_address': request.META['REMOTE_ADDR'],
            'fingerprint_session_id': request.session.get(CHECKOUT_FINGERPRINT_SESSION_ID),
            'extra_fields': extra_fields,
        })

        # Return form fields to the browser. The browser then needs to fill in the blank
        # fields (like billing data) and submit them as a POST to CyberSource.
        url, fields = self._fields(operation)

        # Return a response showing we need to post some fields to the given
        # URL to finishing processing this payment method
        return FormPostRequired(
            amount=amount,
            name='get-token-and-authorize',
            url=url,
            fields=fields)


    # Payment Step 2
    def record_successful_authorization(self, reply_log_entry, order, data):
        token = self._save_token(
            reply_log_entry=reply_log_entry,
            token_string=data.get('payment_token'),
            card_num=data.get('req_card_number'),
            card_type=data.get('req_card_type'))

        auth_amount = Decimal(data.get('auth_amount', '0'))
        req_amount = Decimal(data.get('req_amount', '0'))

        source = self.get_source(order, data.get('transaction_id'))
        source.amount_allocated += auth_amount
        source.save()

        transaction = Transaction()
        transaction.log = reply_log_entry
        transaction.source = source
        transaction.token = token
        transaction.txn_type = Transaction.AUTHORISE
        transaction.amount = req_amount
        transaction.reference = data.get('transaction_id')
        transaction.status = data.get('decision')
        transaction.request_token = data.get('request_token')
        transaction.processed_datetime = datetime.strptime(data.get('signed_date_time'), settings.DATE_FORMAT)
        transaction.save()

        event = self.make_authorize_event(order, auth_amount, data.get('transaction_id'))
        for line in order.lines.all():
            self.make_event_quantity(event, line, line.quantity)

        return Complete(source.amount_allocated)


    def _save_token(self, reply_log_entry, token_string, card_num, card_type):
        """Helper to insupd a payment token object"""
        tokens = PaymentToken.objects.filter(token=token_string)
        if tokens.exists():
            return tokens.first()

        token = PaymentToken(
            log=reply_log_entry,
            token=token_string,
            masked_card_number=card_num,
            card_type=card_type)
        token.save()
        return token


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
