from datetime import datetime
from decimal import Decimal
from django.db.models import F
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from oscar.core.loading import get_model, get_class
from oscarapicheckout.states import Complete, Declined
from oscarapicheckout.methods import PaymentMethod
from oscarapicheckout import utils
from .constants import PRECISION, DECISION_ACCEPT, DECISION_REVIEW
from .utils import encrypt_session_id
from .models import PaymentToken, CyberSourceReply
from .cybersoap import CyberSourceSoap
from . import settings, signature, models
import dateutil.parser
import random
import time
import re
import logging

logger = logging.getLogger(__name__)

Transaction = get_model("payment", "Transaction")
OrderNote = get_model("order", "OrderNote")
InvalidOrderStatus = get_class("order.exceptions", "InvalidOrderStatus")


class SecureAcceptanceAction(object):
    currency = settings.DEFAULT_CURRENCY
    date_format = settings.DATE_FORMAT
    locale = settings.LOCALE
    transaction_type = ""

    def __init__(self, server_hostname):
        self.profile = models.SecureAcceptanceProfile.get_profile(server_hostname)

    @property
    def signed_field_names(self):
        return set(
            [
                "access_key",
                "profile_id",
                "transaction_uuid",
                "signed_field_names",
                "unsigned_field_names",
                "signed_date_time",
                "locale",
                "transaction_type",
            ]
        )

    @property
    def unsigned_field_names(self):
        return set([])

    def fields(self):
        names = self.signed_field_names | self.unsigned_field_names
        fields = {name: "" for name in names}

        data, signed_fields = self.build_request_data()
        fields.update(data)

        signed_fields = signed_fields | set(
            ["signed_date_time", "signed_field_names", "unsigned_field_names"]
        )
        unsigned_fields = set(fields.keys()) - signed_fields
        fields["signed_date_time"] = datetime.utcnow().strftime(self.date_format)
        fields["signed_field_names"] = ",".join(signed_fields)
        fields["unsigned_field_names"] = ",".join(unsigned_fields)

        signer = signature.SecureAcceptanceSigner(self.profile.secret_key)
        fields["signature"] = signer.sign(fields, signed_fields)
        return fields

    def build_request_data(self):
        data = {
            "access_key": self.profile.access_key,
            "currency": self.currency,
            "locale": self.locale,
            "profile_id": self.profile.profile_id,
            "transaction_type": self.transaction_type,
            "transaction_uuid": self.generate_uuid(),
        }

        data.update(self.build_signed_data())
        signed_fields = self.signed_field_names | set(data.keys())
        data.update(self.build_unsigned_data())
        return data, signed_fields

    def build_signed_data(self):
        return {}

    def build_unsigned_data(self):
        return {}

    def generate_uuid(self):
        return "%s%s" % (int(time.time()), random.randrange(0, 100))


class SecureAcceptanceShippingAddressMixin(object):
    def _get_shipping_signed_fields(self):
        return set(
            [
                "ship_to_forename",
                "ship_to_surname",
                "ship_to_address_line1",
                "ship_to_address_line2",
                "ship_to_address_city",
                "ship_to_address_state",
                "ship_to_address_postal_code",
                "ship_to_address_country",
                "ship_to_phone",
                "shipping_method",
            ]
        )

    def _get_shipping_unsigned_fields(self):
        return set([])

    def _get_shipping_data(self):
        order_shipping_code = str(self.order.shipping_code)
        cs_shipping_code = settings.SHIPPING_METHOD_MAPPING.get(
            order_shipping_code, settings.SHIPPING_METHOD_DEFAULT
        )
        shipping_data = {"shipping_method": cs_shipping_code}

        if self.order.shipping_address:
            shipping_data["ship_to_forename"] = self.order.shipping_address.first_name
            shipping_data["ship_to_surname"] = self.order.shipping_address.last_name
            shipping_data["ship_to_address_line1"] = self.order.shipping_address.line1
            shipping_data["ship_to_address_line2"] = self.order.shipping_address.line2
            shipping_data["ship_to_address_city"] = self.order.shipping_address.line4
            shipping_data["ship_to_address_state"] = self.order.shipping_address.state
            shipping_data["ship_to_address_postal_code"] = (
                self.order.shipping_address.postcode
            )
            shipping_data["ship_to_address_country"] = (
                self.order.shipping_address.country.code
            )
            shipping_data["ship_to_phone"] = re.sub(
                "[^0-9]", "", self.order.shipping_address.phone_number.as_rfc3966
            )

        return shipping_data


class SecureAcceptanceBillingAddressMixin(object):
    def _get_billing_signed_fields(self):
        return set(
            [
                "bill_to_forename",
                "bill_to_surname",
                "bill_to_address_line1",
                "bill_to_address_line2",
                "bill_to_address_city",
                "bill_to_address_state",
                "bill_to_address_postal_code",
                "bill_to_address_country",
                "bill_to_email",
            ]
        )

    def _get_billing_unsigned_fields(self):
        return set(
            [
                # Oscar doesn't track phone number for billing addresses. Set this as unsigned to that the client JS can specify it if they want.
                "bill_to_phone",
            ]
        )

    def _get_billing_data(self):
        data = {
            "bill_to_email": self.order.email,
        }
        if self.order.billing_address:
            data["bill_to_forename"] = self.order.billing_address.first_name
            data["bill_to_surname"] = self.order.billing_address.last_name
            data["bill_to_address_line1"] = self.order.billing_address.line1
            data["bill_to_address_line2"] = self.order.billing_address.line2
            data["bill_to_address_city"] = self.order.billing_address.line4
            data["bill_to_address_state"] = self.order.billing_address.state
            data["bill_to_address_postal_code"] = self.order.billing_address.postcode
            data["bill_to_address_country"] = self.order.billing_address.country.code
        return data


class SecureAcceptanceOrderAction(
    SecureAcceptanceAction,
    SecureAcceptanceShippingAddressMixin,
    SecureAcceptanceBillingAddressMixin,
):
    """
    Abstract SecureAcceptanceAction for action's related to orders.
    """

    method_key_field_name = "merchant_defined_data50"
    session_id_field_name = "merchant_secure_data4"  # Use secure_data4 because it has a 2000 char length limit, as opposed to 100 char.

    def __init__(
        self, session_id, order, method_key, amount, server_hostname, **kwargs
    ):
        self.session_id = session_id
        self.order = order
        self.method_key = method_key
        self.amount = amount
        self.customer_ip_address = kwargs.get("customer_ip_address")
        self.device_fingerprint_id = kwargs.get("fingerprint_session_id")
        self.extra_fields = kwargs.get("extra_fields")
        super().__init__(server_hostname)

    @property
    def signed_field_names(self):
        fields = super().signed_field_names
        fields = fields | self._get_shipping_signed_fields()
        fields = fields | self._get_billing_signed_fields()
        fields = fields | set(
            [
                "payment_method",
                "reference_number",
                "currency",
                "amount",
                "line_item_count",
                "customer_ip_address",
                "device_fingerprint_id",
                self.method_key_field_name,
                self.session_id_field_name,
            ]
        )
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
        data["payment_method"] = "card"
        data["reference_number"] = str(self.order.number)
        data["currency"] = self.order.currency
        data[self.method_key_field_name] = self.method_key
        data[self.session_id_field_name] = encrypt_session_id(self.session_id)
        data["amount"] = str(self.amount.quantize(PRECISION))

        # Add shipping and billing info
        data.update(self._get_shipping_data())
        data.update(self._get_billing_data())

        # Add line item info
        i = 0
        for line in self.order.lines.all():
            data["item_%s_name" % i] = line.product.title
            data["item_%s_sku" % i] = line.partner_sku
            data["item_%s_quantity" % i] = str(line.quantity)
            data["item_%s_unit_price" % i] = str(
                line.unit_price_incl_tax.quantize(PRECISION)
            )
            i += 1
        data["line_item_count"] = str(i)

        # Other misc fields
        for field in ("customer_ip_address", "device_fingerprint_id"):
            value = getattr(self, field, None)
            if value is not None:
                data[field] = value

        # Extra fields
        for k, v in self.extra_fields.items():
            data["merchant_defined_data{}".format(k)] = v

        data.update(self.extra_fields)

        return data


class CreatePaymentToken(SecureAcceptanceOrderAction):
    transaction_type = "create_payment_token"
    url = settings.ENDPOINT_PAY

    @property
    def unsigned_field_names(self):
        fields = super().unsigned_field_names
        fields = fields | set(
            [
                # There are unsigned as the server should *never* know them. The client JS must fill them in.
                "card_type",
                "card_number",
                "card_expiry_date",
                "card_cvn",
            ]
        )
        return fields


class ReplyHandlerAction(PaymentMethod):
    name = settings.SOURCE_TYPE

    def __init__(self, reply_log_entry, request, method_key):
        self.reply_log_entry = reply_log_entry
        self.request = request
        self.method_key = method_key

    def create_order_note(self, order, msg):
        return OrderNote.objects.create(
            note_type=OrderNote.SYSTEM, order=order, message=msg
        )


class RecordPaymentToken(ReplyHandlerAction):
    def __call__(self, token_string, card_num, card_type):
        """Record the generated payment token and require authorization using the token."""
        try:
            token = PaymentToken.objects.filter(token=token_string).get()
        except PaymentToken.DoesNotExist:
            token = PaymentToken(
                log=self.reply_log_entry,
                token=token_string,
                masked_card_number=card_num,
                card_type=card_type,
            )
            token.save()
        return token


class RecordSuccessfulAuth(ReplyHandlerAction):
    def __call__(self, order, token_string, response, update_session=False):
        decision = self.reply_log_entry.get_decision()
        transaction_id = response.requestID
        request_token = response.requestToken
        signed_date_time = response.ccAuthReply.authorizedDateTime
        req_amount = Decimal(response.ccAuthReply.amount)
        # assuming these are equal since authorization succeeded
        auth_amount = req_amount
        source = self.get_source(order, transaction_id)

        # Lookup the payment token
        try:
            token = PaymentToken.objects.get(token=token_string)
        except PaymentToken.DoesNotExist:
            return Declined(req_amount, source_id=source.pk)
        # Increment the amount_allocated on the payment source
        source.amount_allocated = F("amount_allocated") + auth_amount
        source.save()
        source.refresh_from_db()  # Refetch data from DB to resolve F() expression
        # Save a new transaction record
        transaction = Transaction()
        transaction.log = self.reply_log_entry
        transaction.source = source
        transaction.token = token
        transaction.txn_type = Transaction.AUTHORISE
        transaction.amount = req_amount
        transaction.reference = transaction_id
        transaction.status = decision
        transaction.request_token = request_token
        transaction.processed_datetime = dateutil.parser.parse(signed_date_time)
        transaction.save()
        # Create payment event
        event = self.make_authorize_event(order, auth_amount)
        for line in order.lines.all():
            self.make_event_quantity(event, line, line.quantity)
        # Create order notes
        if response.decision == DECISION_REVIEW:
            self.create_review_order_note(order, response.requestID)
        # Update payment state in session
        new_state = Complete(source.amount_allocated, source_id=source.pk)
        if update_session:
            utils.update_payment_method_state(
                order, self.request, self.method_key, new_state
            )
        return new_state

    def create_review_order_note(self, order, transaction_id):
        """If an order is under review, add a note explaining why"""
        msg = _(
            "Transaction %(transaction_id)s is currently under review. Use Decision Manager to either accept or reject the transaction."
        ) % dict(transaction_id=transaction_id)
        self.create_order_note(order, msg)


class RecordDeclinedAuth(ReplyHandlerAction):
    def __call__(self, order, token_string, response, amount, update_session=False):
        decision = self.reply_log_entry.get_decision()
        transaction_id = response.requestID
        request_token = response.requestToken
        signed_date_time = str(timezone.now())  # not available in response.ccAuthReply
        req_amount = amount  # not available in response.ccAuthReply
        # Save a transaction to the DB
        source = self.get_source(order, transaction_id)
        transaction = Transaction()
        transaction.log = self.reply_log_entry
        transaction.source = source
        transaction.token = PaymentToken.objects.filter(token=token_string).first()
        transaction.txn_type = Transaction.AUTHORISE
        transaction.amount = req_amount
        transaction.reference = transaction_id
        transaction.status = decision
        transaction.request_token = request_token
        transaction.processed_datetime = dateutil.parser.parse(signed_date_time)
        transaction.save()
        # Update payment state in session
        if update_session:
            try:
                utils.mark_payment_method_declined(
                    order, self.request, self.method_key, amount
                )
            except InvalidOrderStatus:
                logger.exception(
                    "Failed to set Order %s to payment declined. Order is current in status %s. Examine CyberSourceReply[%s]",
                    order.number,
                    order.status,
                    self.reply_log_entry.pk,
                )
        return Declined(req_amount, source_id=source.pk)


class RecordCapture(ReplyHandlerAction):
    def __call__(
        self,
        order,
        capture_resp,
        authorization_txn,
        capture_amount,
    ):
        try:
            processed_dt = dateutil.parser.parse(
                capture_resp.ccCaptureReply.requestDateTime
            )
        except AttributeError:
            processed_dt = timezone.now()
        source = authorization_txn.source
        transaction = Transaction()
        transaction.log = self.reply_log_entry
        transaction.source = source
        transaction.token = authorization_txn.token
        transaction.authorization = authorization_txn
        transaction.txn_type = Transaction.DEBIT
        transaction.amount = capture_amount
        transaction.reference = capture_resp.requestID
        transaction.status = self.reply_log_entry.get_decision()
        transaction.request_token = capture_resp.requestToken
        transaction.processed_datetime = processed_dt
        transaction.save()

        # If the transaction was successful, increment that amount debited and create a payment event
        if transaction.status in (DECISION_ACCEPT, DECISION_REVIEW):
            source.amount_debited = F("amount_debited") + capture_amount
            source.save()
            event = self.make_debit_event(order, capture_amount)
            for line in order.lines.all():
                self.make_event_quantity(event, line, line.quantity)
        # Return the resulting transaction
        return transaction


class SOAPAction:
    def __init__(self, order, request=None, method_key=None):
        self.order = order
        self.request = request
        self.method_key = method_key
        self.api = CyberSourceSoap(
            wsdl=settings.CYBERSOURCE_WSDL,
            merchant_id=settings.MERCHANT_ID,
            transaction_security_key=settings.CYBERSOURCE_SOAP_KEY,
            order=order,
            request=request,
            method_key=method_key,
        )


class GetPaymentToken(SOAPAction):
    def __call__(self, payment_data):
        response = self.api.get_token(payment_data)
        reply_log_entry = CyberSourceReply.log_soap_response(
            order=self.order,
            response=response,
            request=self.request,
        )
        # If token creation was not successful, return
        if response.decision != DECISION_ACCEPT:
            return None, None
        # Lookup more details about the token
        token_string = response.paySubscriptionCreateReply.subscriptionID
        token_details = self.api.lookup_payment_token(token_string)
        if token_details is None:
            return None, None
        # Record the new payment token
        token = RecordPaymentToken(reply_log_entry, self.request, self.method_key)(
            token_string=token_string,
            card_num=token_details.paySubscriptionRetrieveReply.cardAccountNumber,
            card_type=token_details.paySubscriptionRetrieveReply.cardType,
        )
        if token is None:
            return None, None
        # Use the token details to update our copy of the card's expiration date.
        expiry_date = "{month}-{year}".format(
            month=token_details.paySubscriptionRetrieveReply.cardExpirationMonth,
            year=token_details.paySubscriptionRetrieveReply.cardExpirationYear,
        )
        reply_log_entry.req_card_expiry_date = expiry_date
        reply_log_entry.save()
        # Return the token object
        return token, reply_log_entry


class AuthorizePayment(SOAPAction):
    def __call__(self, token_string, amount, update_session, card_expiry_date=None):
        response = self.api.authorize(
            token=token_string,
            amount=amount,
        )
        reply_log_entry = CyberSourceReply.log_soap_response(
            order=self.order,
            response=response,
            request=self.request,
            card_expiry_date=card_expiry_date,
        )
        record_kwargs = {
            "reply_log_entry": reply_log_entry,
            "request": self.request,
            "method_key": self.method_key,
        }
        if response.decision in (DECISION_ACCEPT, DECISION_REVIEW):
            state = RecordSuccessfulAuth(**record_kwargs)(
                order=self.order,
                token_string=token_string,
                response=response,
                update_session=update_session,
            )
        else:
            state = RecordDeclinedAuth(**record_kwargs)(
                order=self.order,
                token_string=token_string,
                response=response,
                amount=amount,
                update_session=update_session,
            )
        return state


class CapturePayment(SOAPAction):
    def __call__(self, authorization_txn, amount):
        """
        Given a successful authorization transaction, submit a capture funds request.
        """
        # Sanity check that the given transaction matches what we'd expect (and
        # isn't, for example, from another payment source or a declined status).
        can_capture, err_reason = authorization_txn.can_be_captured
        if not can_capture:
            raise ValueError(err_reason)

        # Check the given amount
        if amount > authorization_txn.get_remaining_amount_to_capture():
            raise ValueError(
                "Capture amount can not be greater than the amount of the source authorization"
            )

        # Attempt to capture payment for this authorization
        order = authorization_txn.source.order
        capture_resp = self.api.capture(
            token=authorization_txn.token.token,
            amount=amount,
            auth_request_id=authorization_txn.reference,
        )
        reply_log_entry = CyberSourceReply.log_soap_response(order, capture_resp)

        # Record a debit transaction and return it
        transaction = RecordCapture(reply_log_entry, None, None)(
            order=order,
            capture_resp=capture_resp,
            authorization_txn=authorization_txn,
            capture_amount=amount,
        )
        return transaction
