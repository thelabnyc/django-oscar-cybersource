from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any, Literal
import logging

from django.dispatch import Signal
from django.http import HttpRequest
from suds.wsse import Security, UsernameToken
import soap

from . import signals
from .constants import CHECKOUT_FINGERPRINT_SESSION_ID, PRECISION, TERMINAL_DESCRIPTOR

if TYPE_CHECKING:
    from oscar.apps.order.models import Order

logger = logging.getLogger(__name__)


type SoapRequest = dict[str, Any]
type SoapResponse = Any


class CyberSourceSoap:
    """
    Wrapper around the Cybersource SOAP API.

    The given WSDL should be one of the following:

    - Test Environments: ``https://ics2wstesta.ic3.com/commerce/1.x/transactionProcessor/CyberSourceTransaction_1.141.wsdl``
    - Production Environments: ``https://ics2wsa.ic3.com/commerce/1.x/transactionProcessor/CyberSourceTransaction_1.141.wsdl``

    MerchantID should be your Cybersource account's merchant ID. Transaction security key should be a SOAP Toolkit API Security
    Keys. You can make find this in the Cybersource Business Center => Transaction Security Keys => Security Keys for the SOAP
    Toolkit API => Generate Key. It is be secret and not be checked into source-control. Treat this like a password.
    """

    def __init__(
        self,
        wsdl: str,
        merchant_id: str,
        transaction_security_key: str,
        order: Order,
        request: HttpRequest | None = None,
        method_key: str | None = "",
        soap_log_prefix: str = "CYBERSOURCE",
    ):
        self.merchant_id = merchant_id
        self.order = order
        self.request = request
        self.method_key = method_key

        # Build a SOAP client
        self.client = soap.get_client(wsdl, soap_log_prefix)

        # Add WSSE Security Header to client
        security = Security()
        token = UsernameToken(self.merchant_id, transaction_security_key)
        security.tokens.append(token)
        self.client.set_options(wsse=security)

    def get_token(self, encrypted_payment_data: str) -> SoapResponse:
        """Get a token using encrypted card number"""
        txndata = self._prep_transaction("paySubscriptionCreateService", "0")
        # Add encrypted payment data (from the Bluefin terminal)
        txndata["encryptedPayment"] = self.client.factory.create("ns0:encryptedPayment")
        txndata["encryptedPayment"].data = encrypted_payment_data
        txndata["encryptedPayment"].descriptor = TERMINAL_DESCRIPTOR
        # Add extra fields
        self._trigger_pre_build_hook(txndata, signals.pre_build_get_token_request)
        # Add token request
        txndata["recurringSubscriptionInfo"] = self.client.factory.create(
            "ns0:recurringSubscriptionInfo"
        )
        txndata["recurringSubscriptionInfo"].frequency = "on-demand"
        # Run transaction
        return self._run_transaction(txndata)

    def lookup_payment_token(self, token: str) -> SoapResponse:
        """Using a payment token, lookup some of the details about the related card"""
        txndata = self._prep_transaction("paySubscriptionRetrieveService", "0")
        # Add token info
        txndata["recurringSubscriptionInfo"] = self.client.factory.create(
            "ns0:recurringSubscriptionInfo"
        )
        txndata["recurringSubscriptionInfo"].subscriptionID = token
        # Run transaction
        return self._run_transaction(txndata)

    def authorize(self, token: str, amount: Decimal) -> SoapResponse:
        """Authorize with a payment token"""
        txndata = self._prep_transaction("ccAuthService", amount)
        # Add token info
        txndata["recurringSubscriptionInfo"] = self.client.factory.create(
            "ns0:recurringSubscriptionInfo"
        )
        txndata["recurringSubscriptionInfo"].subscriptionID = token
        # Add extra fields
        self._trigger_pre_build_hook(
            txndata, signals.pre_build_auth_request, token=token
        )
        # Run transaction
        return self._run_transaction(txndata)

    def capture(
        self, token: str, amount: Decimal, auth_request_id: str
    ) -> SoapResponse:
        """Authorize with a payment token"""
        txndata = self._prep_transaction("ccCaptureService", amount)
        # Add token info
        txndata["recurringSubscriptionInfo"] = self.client.factory.create(
            "ns0:recurringSubscriptionInfo"
        )
        txndata["recurringSubscriptionInfo"].subscriptionID = token
        # Add request ID of the cooresponding authorization
        txndata["ccCaptureService"]["authRequestID"] = auth_request_id
        # Add extra fields
        self._trigger_pre_build_hook(
            txndata, signals.pre_build_capture_request, token=token
        )
        # Run transaction
        return self._run_transaction(txndata)

    def _prep_transaction(
        self,
        service: Literal[
            "paySubscriptionCreateService",
            "paySubscriptionRetrieveService",
            "ccAuthService",
            "ccCaptureService",
        ],
        amount: Decimal | str,
    ) -> SoapRequest:
        data: SoapRequest = {}

        # Add which service to run (auth/capture/etc)
        data[service] = self.client.factory.create("ns0:{}".format(service))
        data[service]._run = "true"

        # Add merchant info
        if self.request and CHECKOUT_FINGERPRINT_SESSION_ID:
            fingerprint_id = self.request.session.get(CHECKOUT_FINGERPRINT_SESSION_ID)
            if fingerprint_id:
                data["deviceFingerprintID"] = fingerprint_id
        data["merchantID"] = self.merchant_id
        data["merchantReferenceCode"] = self.order.number

        # Add order info
        data["billTo"] = self.client.factory.create("ns0:BillTo")
        data["billTo"].email = self.order.email
        if self.request:
            data["billTo"].ipAddress = self.request.META.get("REMOTE_ADDR")
        if self.order.user:
            data["billTo"].customerID = self.order.user.pk

        # Add order billing data
        if self.order.billing_address:
            data["billTo"].firstName = self.order.billing_address.first_name
            data["billTo"].lastName = self.order.billing_address.last_name
            data["billTo"].street1 = self.order.billing_address.line1
            data["billTo"].street2 = self.order.billing_address.line2
            data["billTo"].city = self.order.billing_address.line4
            data["billTo"].state = self.order.billing_address.state
            data["billTo"].postalCode = self.order.billing_address.postcode
            data["billTo"].country = self.order.billing_address.country.iso_3166_1_a2

        # Add order shipping data
        if self.order.shipping_address:
            data["shipTo"] = self.client.factory.create("ns0:ShipTo")
            data["shipTo"].phoneNumber = self.order.shipping_address.phone_number
            data["shipTo"].firstName = self.order.shipping_address.first_name
            data["shipTo"].lastName = self.order.shipping_address.last_name
            data["shipTo"].street1 = self.order.shipping_address.line1
            data["shipTo"].street2 = self.order.shipping_address.line2
            data["shipTo"].city = self.order.shipping_address.line4
            data["shipTo"].state = self.order.shipping_address.state
            data["shipTo"].postalCode = self.order.shipping_address.postcode
            data["shipTo"].country = self.order.shipping_address.country.iso_3166_1_a2

        # Add line items
        data["item"] = []
        i = 0
        for line in self.order.lines.all():
            item = self.client.factory.create("ns0:Item")
            item._id = str(i)
            item.productName = line.product.title if line.product is not None else ""
            item.productSKU = line.partner_sku
            item.quantity = str(line.quantity)
            item.unitPrice = str(
                line.unit_price_incl_tax.quantize(PRECISION)
                if line.unit_price_incl_tax is not None
                else ""
            )
            data["item"].append(item)
            i += 1

        # Add order total data
        data["purchaseTotals"] = self.client.factory.create("ns0:PurchaseTotals")
        data["purchaseTotals"].currency = self.order.currency
        data["purchaseTotals"].grandTotalAmount = amount if amount is not None else "0"

        # Prep is done
        return data

    def _trigger_pre_build_hook(
        self,
        txndata: SoapRequest,
        signal: Signal,
        token: str | None = None,
    ) -> None:
        """
        Send a Django signal as a means of allowing applications to modify the merchantDefinedData fields in the
        transaction before we run it.
        """
        extra_fields: dict[str, Any] = {}
        signal.send(
            sender=self.__class__,
            extra_fields=extra_fields,
            request=self.request,
            order=self.order,
            token=token,
            method_key=self.method_key,
        )
        txndata["merchantDefinedData"] = self.client.factory.create(
            "ns0:MerchantDefinedData"
        )
        for k, v in extra_fields.items():
            txndata["merchantDefinedData"]["field{}".format(k)] = v

    def _run_transaction(self, txndata: SoapRequest) -> SoapResponse:
        """Send the transaction to Cybersource to process"""
        try:
            response = self.client.service.runTransaction(**txndata)
        except Exception:
            logger.exception(
                "Failed to run Cybersource SOAP transaction on Order {}".format(
                    self.order.number
                )
            )
            response = None
        return response
