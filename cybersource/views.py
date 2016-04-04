from datetime import datetime
from decimal import Decimal
from django.contrib import messages
from django.core.exceptions import SuspiciousOperation
from django.core.urlresolvers import reverse
from django.db import transaction
from django.http import Http404
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.views import generic
from django.views.decorators.csrf import csrf_exempt
from django_statsd.clients import statsd
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from oscar.core.loading import get_class, get_model
from oscarapi.basket.operations import assign_basket_strategy
from oscarapi.views.utils import BasketPermissionMixin
from . import actions, settings, signals, signature
from .authentication import CSRFExemptSessionAuthentication
from .constants import CHECKOUT_BASKET_ID, CHECKOUT_ORDER_ID, CHECKOUT_ORDER_NUM, CHECKOUT_SHIPPING_CODE, CHECKOUT_FINGERPRINT_SESSION_ID
from .models import CyberSourceReply, PaymentToken
from .serializers import CheckoutSerializer
import uuid
import logging

OrderNumberGenerator = get_class('order.utils', 'OrderNumberGenerator')
OrderPlacementMixin = get_class('checkout.mixins', 'OrderPlacementMixin')
OrderTotalCalculator = get_class('checkout.calculators', 'OrderTotalCalculator')

Basket = get_model('basket', 'Basket')
BillingAddress = get_model('order', 'BillingAddress')
Country = get_model('address', 'Country')
Order = get_model('order', 'Order')
PaymentEventType = get_model('order', 'PaymentEventType')
PaymentEvent = get_model('order', 'PaymentEvent')
PaymentEventQuantity = get_model('order', 'PaymentEventQuantity')
ShippingAddress = get_model('order', 'ShippingAddress')
Source = get_model('payment', 'Source')
SourceType = get_model('payment', 'SourceType')
Transaction = get_model('payment', 'Transaction')


logger = logging.getLogger(__name__)



class FingerprintRedirectView(generic.View):
    protocol = settings.FINGERPRINT_PROTOCOL
    host = settings.FINGERPRINT_HOST
    url_types = {
        'img-1': '%(protocol)s://%(host)s/fp/clear.png?org_id=%(org_id)s&session_id=%(merchant_id)s%(session_id)s&m=1',
        'img-2': '%(protocol)s://%(host)s/fp/clear.png?org_id=%(org_id)s&session_id=%(merchant_id)s%(session_id)s&m-2',
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
            'protocol': self.protocol,
            'host': self.host,
            'org_id': settings.ORG_ID,
            'merchant_id': settings.MERCHANT_ID,
            'session_id': sessid,
        }
        url = self.url_types[url_type] % data
        return redirect(url)



class BaseCheckoutView(BasketPermissionMixin, APIView):
    def get_checkout_serializer(self, request, data):
        context = {'request': request}
        ser = CheckoutSerializer(data=data, context=context)
        ser.order_number = request.session.get(CHECKOUT_ORDER_NUM)
        return ser



class SignAuthorizePaymentFormView(BaseCheckoutView):
    """
    Provide the form fields needed to make a signed authorization transaction request to CyberSource.
    """
    def post(self, request, format=None):
        data_basket = self.get_data_basket(request.data, format)
        basket = self.check_basket_permission(request, basket_pk=data_basket.pk)
        assert(data_basket == basket)

        # Validate the shipping address, etc
        ser = self.get_checkout_serializer(request, request.data)
        if not ser.is_valid():
            return Response(ser.errors, status.HTTP_406_NOT_ACCEPTABLE)

        basket = ser.validated_data['basket']
        shipping_charge = ser.validated_data['shipping_charge']
        guest_email = ser.validated_data.get('guest_email')
        shipping_address = None
        if ser.validated_data.get('shipping_address'):
            shipping_address = ShippingAddress(**ser.validated_data['shipping_address'])
        billing_address = None
        if ser.validated_data.get('billing_address'):
            billing_address = BillingAddress(**ser.validated_data['billing_address'])

        # Freeze the basket so that the user can't modify it anymore, preventing any sort
        # of possible authorization / add product timing attack.
        request.session[CHECKOUT_BASKET_ID] = basket.id
        basket.freeze()

        # Allow application to calculate taxes before the total is calculated
        signals.pre_calculate_auth_total.send(
            sender=self.__class__,
            basket=basket,
            shipping_address=shipping_address)

        # Figure out the final total order price
        order_total = OrderTotalCalculator().calculate(basket, shipping_charge)

        # Generate an order number unless we already have one in the session
        order_number = request.session.get(CHECKOUT_ORDER_NUM)
        if not order_number:
            order_number = OrderNumberGenerator().order_number(basket)
            order_number = str(order_number)
            request.session[CHECKOUT_ORDER_NUM] = order_number

        # Cache shipping method code in session
        request.session[CHECKOUT_SHIPPING_CODE] = ser.validated_data['shipping_method'].code

        # Allow application to include extra, arbitrary fields in the request to CS
        extra_fields = { 'bill_to_email': guest_email }
        signals.pre_build_auth_request.send(
            sender=self.__class__,
            extra_fields=extra_fields,
            request=request,
            basket=basket)

        # Build the data for CyberSource transaction
        operation = actions.CreateAndAuthorizePaymentToken(**{
            'order_number': order_number,
            'order_total': order_total,
            'basket': basket,
            'shipping_address': shipping_address,
            'billing_address': billing_address,
            'customer_ip_address': request.META['REMOTE_ADDR'],
            'fingerprint_session_id': request.session.get(CHECKOUT_FINGERPRINT_SESSION_ID),
            'extra_fields': extra_fields,
        })

        # Return form fields to the browser. The browser then needs to fill in the blank
        # fields (like billing data) and submit them as a POST to CyberSource.
        data = dict(zip(('url', 'fields'), self._fields(operation)))
        statsd.incr('checkout.complete-payment-authorize')
        return Response(data)

    def _fields(self, operation):
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



class CyberSourceReplyView(OrderPlacementMixin, BaseCheckoutView):
    """
    Handle a CyberSource reply.
    """
    authentication_classes = (CSRFExemptSessionAuthentication, )

    # Default code for the email to send after successful checkout
    communication_type_code = 'ORDER_PLACED'
    DECISION_ACCEPT = 'ACCEPT'

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
            data=request.data)
        log.save()
        return log


    def get_handler_fn(self, trans_type):
        handlers = {
            actions.CreateAndAuthorizePaymentToken.transaction_type: self.record_authorization,
        }
        if trans_type not in handlers:
            raise SuspiciousOperation("Couldn't find handler for %s" % trans_type)
        return handlers[trans_type]


    def record_authorization(self, request, format, reply_log_entry):
        # If the transaction already exists, do nothing
        if Transaction.objects.filter(reference=request.data.get('transaction_id')).exists():
            logger.warning('Duplicate transaction_id received from CyberSource: %s' % request.data.get('transaction_id'))
            return redirect(settings.REDIRECT_SUCCESS)

        # Compare reference number to the order number cached in the session
        if request.data.get('req_reference_number') != request.session.get(CHECKOUT_ORDER_NUM):
            raise SuspiciousOperation("req_reference_number doesn't match user session")

        # Get the (currently frozen) basket from the session reference
        try:
            basket = Basket.objects.get(id=request.session.get(CHECKOUT_BASKET_ID))
        except Basket.DoesNotExist:
            raise SuspiciousOperation("no basket in session")
        assign_basket_strategy(basket, request)

        # Get the basket and serializer prepared to place an order
        data = self._build_checkout_data(request, basket)
        ser = self.get_checkout_serializer(request, data)
        if not ser.is_valid():
            return Response(ser.errors, status.HTTP_400_BAD_REQUEST)

        # Check if the authorization was declined
        if request.data.get('decision') != self.DECISION_ACCEPT:
            messages.add_message(request._request, messages.ERROR, settings.CARD_REJECT_ERROR)
            basket.thaw()
            return redirect(settings.REDIRECT_FAIL)

        # Everything checks out. Place the order and record the transaction.
        order = ser.save()

        # Save the payment token. We'll need to send this to PnP so they can complete the transaction
        token = self._record_payment_token(request, reply_log_entry)

        # Record the transaction information and, if it was declined, make the user try again
        self._record_payment(order, token, request, reply_log_entry)

        # Mark order as authorized since we've successfully auth'd the card
        order.set_status(settings.ORDER_STATUS_SUCCESS)

        # Run post order placement tasks
        self.send_confirmation_message(order, self.communication_type_code)
        signals.order_placed.send(
            sender=self.__class__,
            order=order)

        # Clean up the session
        for key in (CHECKOUT_BASKET_ID, CHECKOUT_ORDER_NUM, CHECKOUT_SHIPPING_CODE):
            if key in request.session:
                del request.session[key]
                request.session.modified = True

        request.session[CHECKOUT_ORDER_ID] = order.id
        return redirect(settings.REDIRECT_SUCCESS)


    def _build_checkout_data(self, request, basket):
        # Convert the request data from CS into something the CheckoutSerializer can understand
        ship_country = request.data.get('req_ship_to_address_country')
        bill_country = request.data.get('req_bill_to_address_country')
        data = {
            'basket': reverse('basket-detail', args=(basket.id, )),
            'guest_email': request.data.get('req_bill_to_email'),
            'shipping_method_code': request.session.get(CHECKOUT_SHIPPING_CODE),
            'shipping_address': None if not ship_country else {
                'first_name': request.data.get('req_ship_to_forename'),
                'last_name': request.data.get('req_ship_to_surname'),
                'line1': request.data.get('req_ship_to_address_line1'),
                'line2': request.data.get('req_ship_to_address_line2', ''),
                'line4': request.data.get('req_ship_to_address_city'),
                'postcode': request.data.get('req_ship_to_address_postal_code'),
                'state': request.data.get('req_ship_to_address_state'),
                'country': reverse('country-detail', args=(ship_country, )),
                'phone_number': '+%s' % request.data.get('req_ship_to_phone'),
            },
            'billing_address': None if not bill_country else {
                'first_name': request.data.get('req_bill_to_forename'),
                'last_name': request.data.get('req_bill_to_surname'),
                'line1': request.data.get('req_bill_to_address_line1'),
                'line2': request.data.get('req_bill_to_address_line2', ''),
                'line4': request.data.get('req_bill_to_address_city'),
                'postcode': request.data.get('req_bill_to_address_postal_code'),
                'state': request.data.get('req_bill_to_address_state'),
                'country': reverse('country-detail', args=(bill_country, )),
            }
        }
        return data


    def _record_payment_token(self, request, reply_log_entry):
        tokens = PaymentToken.objects.filter(token=request.data.get('payment_token'))
        if tokens.exists():
            return tokens.first()

        token = PaymentToken(
            log=reply_log_entry,
            token=request.data.get('payment_token'),
            masked_card_number=request.data.get('req_card_number'),
            card_type=request.data.get('req_card_type'))
        token.save()
        return token


    def _record_payment(self, order, token, request, reply_log_entry):
        source_type, created = SourceType.objects.get_or_create(name=settings.SOURCE_TYPE)
        source, created = Source.objects.get_or_create(order=order, source_type=source_type)
        source.currency = request.data.get('req_currency')
        source.amount_allocated += Decimal(request.data.get('auth_amount', '0'))
        source.save()

        transaction = Transaction()
        transaction.log = reply_log_entry
        transaction.source = source
        transaction.token = token
        transaction.txn_type = Transaction.AUTHORISE
        transaction.amount = request.data.get('req_amount', 0)
        transaction.reference = request.data.get('transaction_id')
        transaction.status = request.data.get('decision')
        transaction.request_token = request.data.get('request_token')
        transaction.processed_datetime = datetime.strptime(request.data.get('signed_date_time'), settings.DATE_FORMAT)
        transaction.save()

        event = PaymentEvent()
        event.order = order
        event.amount = request.data.get('auth_amount', 0)
        event.reference = request.data.get('transaction_id')
        event.event_type = PaymentEventType.objects.get_or_create(name=Transaction.AUTHORISE)[0]
        event.save()

        for line in order.lines.all():
            line_event = PaymentEventQuantity()
            line_event.event = event
            line_event.line = line
            line_event.quantity = line.quantity
            line_event.save()

        return transaction
