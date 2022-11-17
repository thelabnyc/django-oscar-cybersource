from decimal import Decimal
from django.core.exceptions import SuspiciousOperation
from django.db import transaction
from django.http import Http404
from django.shortcuts import redirect, get_object_or_404
from django.views import generic
from lxml import etree
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from oscar.core.loading import get_class, get_model
from oscarapicheckout import utils, states
from oscarapicheckout.settings import ORDER_STATUS_PAYMENT_DECLINED
from .authentication import CSRFExemptSessionAuthentication
from .constants import CHECKOUT_FINGERPRINT_SESSION_ID, DECISION_ACCEPT
from .methods import Cybersource
from .models import SecureAcceptanceProfile, CyberSourceReply
from .signals import received_decision_manager_update
from .utils import decrypt_session_id
from . import actions, settings, signature
import dateutil.parser
import uuid
import logging

InvalidOrderStatus = get_class("order.exceptions", "InvalidOrderStatus")
OrderNumberGenerator = get_class("order.utils", "OrderNumberGenerator")
OrderPlacementMixin = get_class("checkout.mixins", "OrderPlacementMixin")
OrderTotalCalculator = get_class("checkout.calculators", "OrderTotalCalculator")

Order = get_model("order", "Order")
OrderNote = get_model("order", "OrderNote")
Transaction = get_model("payment", "Transaction")


logger = logging.getLogger(__name__)


class FingerprintRedirectView(generic.View):
    url_types = {
        "img-1": "%(protocol)s://%(host)s/fp/clear.png?org_id=%(org_id)s&session_id=%(merchant_id)s%(session_id)s&m=1",
        "img-2": "%(protocol)s://%(host)s/fp/clear.png?org_id=%(org_id)s&session_id=%(merchant_id)s%(session_id)s&m=2",
        "flash": "%(protocol)s://%(host)s/fp/fp.swf?org_id=%(org_id)s&session_id=%(merchant_id)s%(session_id)s",
        "js": "%(protocol)s://%(host)s/fp/check.js?org_id=%(org_id)s&session_id=%(merchant_id)s%(session_id)s",
    }

    def get(self, request, url_type):
        if url_type not in self.url_types:
            raise Http404("url_type not found")

        sessid = request.session.get(CHECKOUT_FINGERPRINT_SESSION_ID)
        if not sessid:
            sessid = str(uuid.uuid1())
            request.session[CHECKOUT_FINGERPRINT_SESSION_ID] = sessid

        data = {
            "protocol": settings.FINGERPRINT_PROTOCOL,
            "host": settings.FINGERPRINT_HOST,
            "org_id": settings.ORG_ID,
            "merchant_id": settings.MERCHANT_ID,
            "session_id": sessid,
        }
        url = self.url_types[url_type] % data
        return redirect(url)


class CyberSourceReplyView(APIView):
    """
    Handle a CyberSource reply.
    """

    authentication_classes = (CSRFExemptSessionAuthentication,)

    def post(self, request, format=None):
        if not self.is_request_valid(request):
            raise SuspiciousOperation("Bad Signature")

        # Resume Session using the encrypted session ID in the Cybersource request
        # Why is this needed?
        # Django 2.2 starts defaulting to sending cookies as SameSite=Lax. Even if you disable that
        # behavior, Chrome>=v80 will treat all cookies as SameSite=Lax.
        #
        # When the session cookie is set to SameSite=Lax, the cookie won't be sent to Django by the
        # Cybersource secure acceptance form POST (the POST which triggers this view). That breaks
        # the mechanism that we use to keep track of checkout payment state.
        #
        # To get around that we store the (encrypted) session ID as merchant defined data sent to
        # Cybersource. Cybersource then sends us that value back with their reply, where we decrypt
        # it, and use it to rehydrate the user's real session.
        session_id_field_name = "req_{}".format(
            actions.SecureAcceptanceOrderAction.session_id_field_name
        )
        encrypted_session_id = request.data.get(session_id_field_name)
        session_id = decrypt_session_id(encrypted_session_id)
        request.session._session_key = session_id
        delattr(request.session, "_session_cache")

        # Record in reply log
        log = CyberSourceReply.log_secure_acceptance_response(
            order=self._get_order(request),
            request=request,
        )

        # Invoke handler for transaction type
        trans_type = request.data.get("req_transaction_type")
        handler = self.get_handler_fn(trans_type)
        with transaction.atomic():
            resp = handler(request, log)

        # Save session and return response
        request.session.save()
        return resp

    def is_request_valid(self, request):
        server_hostname = request.META.get("HTTP_HOST", "")
        profile = SecureAcceptanceProfile.get_profile(server_hostname)
        return signature.SecureAcceptanceSigner(profile.secret_key).verify_request(
            request
        )

    def get_handler_fn(self, trans_type):
        handlers = {
            actions.CreatePaymentToken.transaction_type: self.record_token,
        }
        if trans_type not in handlers:
            raise SuspiciousOperation("Couldn't find handler for %s" % trans_type)
        return handlers[trans_type]

    def record_token(self, request, reply_log_entry):
        # Fetch the related order
        order = self._get_order(request)
        method_key = self._get_method_key(request)
        create_token_resp_data = request.data
        amount = Decimal(request.data.get("req_amount", "0.00"))

        # Figure out what status the order is in.
        token_decision = reply_log_entry.get_decision()

        # Check if the payment token was actually created or not.
        if token_decision != DECISION_ACCEPT:
            # Payment token was not created
            utils.mark_payment_method_declined(order, request, method_key, amount)
            return redirect(settings.REDIRECT_FAIL)

        # Record the new payment token
        token = actions.RecordPaymentToken(reply_log_entry, request, method_key)(
            token_string=create_token_resp_data.get("payment_token"),
            card_num=create_token_resp_data.get("req_card_number"),
            card_type=create_token_resp_data.get("req_card_type"),
        )

        # Try to authorize the payment
        auth_state = actions.AuthorizePayment(order, request, method_key)(
            token_string=token.token,
            amount=amount,
            update_session=True,
        )
        # If authorization was declined, redirect to the failure page.
        if auth_state.status == states.DECLINED:
            return redirect(settings.REDIRECT_FAIL)
        return redirect(settings.REDIRECT_SUCCESS)

    def _get_order(self, request):
        try:
            order = Order.objects.get(number=request.data.get("req_reference_number"))
        except Order.DoesNotExist:
            raise SuspiciousOperation("Order not found.")
        return order

    def _get_method_key(self, request):
        field_name = "req_{}".format(
            actions.SecureAcceptanceOrderAction.method_key_field_name
        )
        return request.data.get(field_name, Cybersource.code)


class DecisionManagerNotificationView(APIView):
    """
    Handle a CyberSource reply.
    """

    authentication_classes = (CSRFExemptSessionAuthentication,)

    def post(self, request, format=None):
        self._check_auth_token(request)
        xml = request.data.get("content").encode()
        root = etree.fromstring(xml)
        # Loop through order updates
        for update in root.xpath("*[local-name()='Update']"):
            try:
                self._handle_update(update)
            except Http404:
                pass
        return Response(status=status.HTTP_200_OK)

    def _check_auth_token(self, request):
        # TODO: This is kind-of lousy to home roll web-hook authentication this way. We should investigate
        # better ways of doing this and, if necessary, make it into it's own package.
        auth_keys = settings.DECISION_MANAGER_KEYS
        if len(auth_keys) == 0:
            return
        auth_key = request.GET.get("key", "").strip()
        if auth_key not in auth_keys:
            raise SuspiciousOperation("Invalid decision manager key")

    @transaction.atomic
    def _handle_update(self, update):
        order = self._get_order(update)
        transaction = self._get_transaction(order, update)

        # Save any notes attached to the order in DM
        for note_elem in update.xpath("*[local-name()='Notes']/*[local-name()='Note']"):
            self._save_order_note(order, note_elem)

        # Update order status
        self._update_decision(order, transaction, update)

        # Send signal to notify other parts of the app that should know
        received_decision_manager_update.send_robust(
            self.__class__, order=order, transaction=transaction, update=update
        )

    def _get_order(self, update):
        order_number = update.attrib["MerchantReferenceNumber"]
        return get_object_or_404(Order, number=order_number)

    def _get_transaction(self, order, update):
        transaction_id = update.attrib["RequestID"]
        try:
            transaction = Transaction.objects.filter(source__order=order).get(
                reference=transaction_id
            )
        except Transaction.DoesNotExist:
            raise Http404()
        return transaction

    def _save_order_note(self, order, note_elem):
        author = note_elem.attrib["AddedBy"]
        comment = note_elem.attrib["Comment"]
        date = dateutil.parser.parse(note_elem.attrib["Date"])

        message_prefix = "[Decision Manager %s]" % date.strftime("%c")
        note = order.notes.filter(
            note_type=OrderNote.SYSTEM, message__startswith=message_prefix
        ).first()
        if not note:
            note = OrderNote(order=order, note_type=OrderNote.SYSTEM, message="")

        note.message += "%s %s added comment: %s\n" % (message_prefix, author, comment)
        note.save()

        return note

    def _update_decision(self, order, transaction, update):
        elems = update.xpath("*[local-name()='NewDecision']")
        if len(elems) <= 0:
            return
        new_decision = elems[0].text

        elems = update.xpath("*[local-name()='Reviewer']")
        reviewer = elems[0].text if len(elems) else ""

        elems = update.xpath("*[local-name()='ReviewerComments']")
        comments = elems[0].text if len(elems) else ""

        note = OrderNote()
        note.order = order
        note.note_type = OrderNote.SYSTEM
        note.message = (
            "[Decision Manager] %s changed decision from %s to %s.\n\nComments: %s"
            % (reviewer, transaction.status, new_decision, comments)
        )
        note.save()

        if new_decision != DECISION_ACCEPT:
            order.status = ORDER_STATUS_PAYMENT_DECLINED
            order.save()

        transaction.status = new_decision
        transaction.save()
