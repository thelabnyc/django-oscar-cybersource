from django.utils.translation import gettext_lazy as _
from django.conf import settings as django_settings
from oscarapicheckout.methods import PaymentMethod, PaymentMethodSerializer
from oscarapicheckout.states import FormPostRequired, Declined
from rest_framework import serializers
from .constants import CHECKOUT_FINGERPRINT_SESSION_ID
from . import actions, signals, settings


class Cybersource(PaymentMethod):
    """
    This is an example of how to implement a payment method that required some off-site
    interaction, like Cybersource Secure Acceptance, for example. It returns a pending
    status initially that requires the client app to make a form post, which in-turn
    redirects back to us. This is a common pattern in PCI SAQ A-EP ecommerce sites.
    """

    name = settings.SOURCE_TYPE
    code = "cybersource"
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
            method_key=method_key,
        )

        # Build the data for CyberSource transaction
        session_id = request.COOKIES.get(django_settings.SESSION_COOKIE_NAME)
        operation = actions.CreatePaymentToken(
            session_id=session_id,
            order=order,
            method_key=method_key,
            amount=amount,
            server_hostname=request.META.get("HTTP_HOST", ""),
            customer_ip_address=request.META["REMOTE_ADDR"],
            fingerprint_session_id=request.session.get(CHECKOUT_FINGERPRINT_SESSION_ID),
            extra_fields=extra_fields,
        )

        # Return form fields to the browser. The browser then needs to fill in the blank
        # fields (like billing data) and submit them as a POST to CyberSource.
        url, fields = self._fields(operation)

        # Return a response showing we need to post some fields to the given
        # URL to finishing processing this payment method
        return FormPostRequired(amount=amount, name="get-token", url=url, fields=fields)

    def _fields(self, operation):
        """Helper to convert an operation object into a list of fields and a URL"""
        fields = []
        cs_fields = operation.fields()
        editable_fields = cs_fields["unsigned_field_names"].split(",")
        for key, value in cs_fields.items():
            fields.append(
                {
                    "key": key,
                    "value": value if isinstance(value, str) else value.decode(),
                    "editable": (key in editable_fields),
                }
            )

        return operation.url, fields


class BluefinPaymentMethodSerializer(PaymentMethodSerializer):
    payment_data = serializers.CharField(max_length=256)

    def validate(self, data):
        if "payment_data" not in data:
            raise serializers.ValidationError(_("Missing encrypted payment data."))
        return super().validate(data)


class Bluefin(PaymentMethod):
    name = settings.SOURCE_TYPE
    code = "bluefin"
    serializer_class = BluefinPaymentMethodSerializer

    def _record_payment(self, request, order, method_key, amount, reference, **kwargs):
        """This is the entry point from django-oscar-api-checkout"""
        payment_data = kwargs.get("payment_data")
        if payment_data is None:
            return Declined(amount)

        # Allow application to include extra, arbitrary fields in the request to CS
        extra_fields = {}
        signals.pre_build_get_token_request.send(
            sender=self.__class__,
            extra_fields=extra_fields,
            request=request,
            order=order,
            method_key=method_key,
        )

        # Get token via SOAP
        token, get_token_log = actions.GetPaymentToken(order, request, method_key)(
            payment_data
        )
        if token is None:
            return Declined(amount)

        # Attempt to authorize payment via SOAP
        new_state = actions.AuthorizePayment(order, request, method_key)(
            token_string=token.token,
            amount=amount,
            update_session=False,
            card_expiry_date=get_token_log.req_card_expiry_date,
        )
        return new_state
