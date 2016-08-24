from decimal import Decimal
from django.contrib import messages
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
from oscarapicheckout import utils
from oscarapicheckout.settings import ORDER_STATUS_PAYMENT_DECLINED
from . import actions, settings, signature
from .authentication import CSRFExemptSessionAuthentication
from .constants import CHECKOUT_FINGERPRINT_SESSION_ID, DECISION_ACCEPT, DECISION_REVIEW
from .methods import Cybersource
from .models import CyberSourceReply
from .signals import received_decision_manager_update
import dateutil.parser
import uuid
import logging

OrderNumberGenerator = get_class('order.utils', 'OrderNumberGenerator')
OrderPlacementMixin = get_class('checkout.mixins', 'OrderPlacementMixin')
OrderTotalCalculator = get_class('checkout.calculators', 'OrderTotalCalculator')

Basket = get_model('basket', 'Basket')
BillingAddress = get_model('order', 'BillingAddress')
Country = get_model('address', 'Country')
Order = get_model('order', 'Order')
OrderNote = get_model('order', 'OrderNote')
PaymentEventType = get_model('order', 'PaymentEventType')
PaymentEvent = get_model('order', 'PaymentEvent')
PaymentEventQuantity = get_model('order', 'PaymentEventQuantity')
ShippingAddress = get_model('order', 'ShippingAddress')
Source = get_model('payment', 'Source')
SourceType = get_model('payment', 'SourceType')
Transaction = get_model('payment', 'Transaction')


logger = logging.getLogger(__name__)



class FingerprintRedirectView(generic.View):
    url_types = {
        'img-1': '%(protocol)s://%(host)s/fp/clear.png?org_id=%(org_id)s&session_id=%(merchant_id)s%(session_id)s&m=1',
        'img-2': '%(protocol)s://%(host)s/fp/clear.png?org_id=%(org_id)s&session_id=%(merchant_id)s%(session_id)s&m=2',
        'flash': '%(protocol)s://%(host)s/fp/fp.swf?org_id=%(org_id)s&session_id=%(merchant_id)s%(session_id)s',
        'js': '%(protocol)s://%(host)s/fp/check.js?org_id=%(org_id)s&session_id=%(merchant_id)s%(session_id)s',
    }

    def get(self, request, url_type):
        if url_type not in self.url_types:
            raise Http404('url_type not found')

        sessid = request.session.get(CHECKOUT_FINGERPRINT_SESSION_ID)
        if not sessid:
            sessid = str(uuid.uuid1())
            request.session[CHECKOUT_FINGERPRINT_SESSION_ID] = sessid

        data = {
            'protocol': settings.FINGERPRINT_PROTOCOL,
            'host': settings.FINGERPRINT_HOST,
            'org_id': settings.ORG_ID,
            'merchant_id': settings.MERCHANT_ID,
            'session_id': sessid,
        }
        url = self.url_types[url_type] % data
        return redirect(url)


class CyberSourceReplyView(APIView):
    """
    Handle a CyberSource reply.
    """
    authentication_classes = (CSRFExemptSessionAuthentication, )


    def post(self, request, format=None):
        if not self.is_request_valid(request):
            raise SuspiciousOperation('Bad Signature')

        # Record in reply log
        log = self.log_response(request)

        # Invoke handler for transaction type
        trans_type = request.data.get('req_transaction_type')
        handler = self.get_handler_fn(trans_type)
        with transaction.atomic():
            resp = handler(request, format, log)
        return resp


    def is_request_valid(self, request):
        return signature.SecureAcceptanceSigner().verify_request(request)


    def log_response(self, request):
        log = CyberSourceReply(
            user=request.user if request.user.is_authenticated() else None,
            order=self._get_order(request),
            data=request.data)
        log.save()
        return log


    def get_handler_fn(self, trans_type):
        handlers = {
            actions.CreatePaymentToken.transaction_type: self.record_token,
            actions.AuthorizePaymentToken.transaction_type: self.record_authorization,
        }
        if trans_type not in handlers:
            raise SuspiciousOperation("Couldn't find handler for %s" % trans_type)
        return handlers[trans_type]


    def record_token(self, request, format, reply_log_entry):
        # Fetch the related order
        order = self._get_order(request)

        # Check if the payment token was actually created or not.
        if request.data.get('decision') != DECISION_ACCEPT:
            messages.add_message(request._request, messages.ERROR, settings.CARD_REJECT_ERROR)
            amount = Decimal(request.data.get('req_amount', '0.00'))
            utils.mark_payment_method_declined(order, request, Cybersource.code, amount)
            return redirect(settings.REDIRECT_FAIL)

        # Token creation was successful, so log it and move on to authorization.
        new_state = Cybersource().record_created_payment_token(request, reply_log_entry, order, request.data)
        utils.update_payment_method_state(order, request, Cybersource.code, new_state)
        return redirect(settings.REDIRECT_PENDING)


    def record_authorization(self, request, format, reply_log_entry):
        # If the transaction already exists, do nothing
        if Transaction.objects.filter(reference=request.data.get('transaction_id')).exists():
            logger.warning('Duplicate transaction_id received from CyberSource: %s' % request.data.get('transaction_id'))
            return redirect(settings.REDIRECT_SUCCESS)

        # Fetch the related order
        order = self._get_order(request)

        is_accept = request.data.get('decision') == DECISION_ACCEPT
        is_under_review = request.data.get('decision') == DECISION_REVIEW

        # If authorization was successful, log it and redirect to the success page.
        if is_accept or is_under_review:
            new_state = Cybersource().record_successful_authorization(reply_log_entry, order, request.data)
            utils.update_payment_method_state(order, request, Cybersource.code, new_state)

            # If the order is under review, add a note explaining why
            if is_under_review:
                msg = (
                    'Transaction %s is currently under review. '
                    'Use Decision Manager to either accept or reject the transaction.'
                ) % request.data.get('transaction_id')
                self._create_order_note(order, msg)

            return redirect(settings.REDIRECT_SUCCESS)

        # Authorization was declined. Show a message to the user.
        messages.add_message(request._request, messages.ERROR, settings.CARD_REJECT_ERROR)
        new_state = Cybersource().record_declined_authorization(reply_log_entry, order, request.data)
        utils.update_payment_method_state(order, request, Cybersource.code, new_state)
        return redirect(settings.REDIRECT_FAIL)


    def _create_order_note(self, order, msg):
        return OrderNote.objects.create(
            note_type=OrderNote.SYSTEM,
            order=order,
            message=msg)


    def _get_order(self, request):
        try:
            order = Order.objects.get(number=request.data.get('req_reference_number'))
        except Order.DoesNotExist:
            raise SuspiciousOperation("Order not found.")
        return order



class DecisionManagerNotificationView(APIView):
    """
    Handle a CyberSource reply.
    """
    authentication_classes = (CSRFExemptSessionAuthentication, )


    def post(self, request, format=None):
        xml = request.data.get('content').encode()
        root = etree.fromstring(xml)
        # Loop through order updates
        for update in root.xpath("*[local-name()='Update']"):
            try:
                self._handle_update(update)
            except Http404:
                pass
        return Response(status=status.HTTP_200_OK)

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
        received_decision_manager_update.send_robust(self.__class__,
            order=order, transaction=transaction, update=update)


    def _get_order(self, update):
        order_number = update.attrib['MerchantReferenceNumber']
        return get_object_or_404(Order, number=order_number)


    def _get_transaction(self, order, update):
        transaction_id = update.attrib['RequestID']
        try:
            transaction = Transaction.objects.filter(source__order=order).get(reference=transaction_id)
        except Transaction.DoesNotExist:
            raise Http404()
        return transaction


    def _save_order_note(self, order, note_elem):
        author = note_elem.attrib['AddedBy']
        comment = note_elem.attrib['Comment']
        date = dateutil.parser.parse(note_elem.attrib['Date'])

        message_prefix = '[Decision Manager %s]' % date.strftime('%c')
        note = order.notes.filter(note_type=OrderNote.SYSTEM, message__startswith=message_prefix).first()
        if not note:
            note = OrderNote(order=order, note_type=OrderNote.SYSTEM, message='')

        note.message += '%s %s added comment: %s\n' % (message_prefix, author, comment)
        note.save()

        return note


    def _update_decision(self, order, transaction, update):
        elems = update.xpath("*[local-name()='NewDecision']")
        if len(elems) <= 0:
            return
        new_decision = elems[0].text

        elems = update.xpath("*[local-name()='Reviewer']")
        reviewer = elems[0].text if len(elems) else ''

        elems = update.xpath("*[local-name()='ReviewerComments']")
        comments = elems[0].text if len(elems) else ''

        note = OrderNote()
        note.order = order
        note.note_type = OrderNote.SYSTEM
        note.message = '[Decision Manager] %s changed decision from %s to %s.\n\nComments: %s' % (
            reviewer, transaction.status, new_decision, comments)
        note.save()

        if new_decision != DECISION_ACCEPT:
            order.set_status(ORDER_STATUS_PAYMENT_DECLINED)

        transaction.status = new_decision
        transaction.save()
