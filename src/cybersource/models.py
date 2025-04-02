from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Literal, Self, cast
import logging

from cryptography.fernet import InvalidToken
from django.contrib.postgres.fields import HStoreField
from django.db import models
from django.db.models import CheckConstraint, Q, QuerySet, Sum
from django.http import HttpRequest
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django_stubs_ext import StrOrPromise
from django_stubs_ext.db.models import TypedModelMeta
from oscar.apps.payment.abstract_models import AbstractTransaction
from oscar.core.compat import AUTH_USER_MODEL
from oscar.models.fields import NullCharField
from rest_framework.request import Request
from thelabdb.fields import EncryptedTextField
import dateutil.parser

from .conf import settings as cyb_settings
from .constants import ZERO, CyberSourceReplyType, Decision
from .cybersoap import SoapResponse
from .utils import zeepobj_to_dict

if TYPE_CHECKING:
    from oscar.apps.order.models import Order

logger = logging.getLogger(__name__)


class SecureAcceptanceProfile(models.Model):
    hostname = models.CharField(
        _("Hostname"),
        max_length=100,
        blank=True,
        unique=True,
        help_text=_(
            "When the request matches this hostname, this profile will be used."
        ),
    )
    profile_id = models.CharField(_("Profile ID"), max_length=50, unique=True)
    access_key = models.CharField(_("Access Key"), max_length=50)
    secret_key = EncryptedTextField(_("Secret Key"))
    is_default = models.BooleanField(
        _("Is Default Profile?"),
        default=False,
        help_text=_(
            "If no profile can be found for a request's hostname, the default profile will be used."
        ),
    )

    class Meta(TypedModelMeta):
        verbose_name = _("Secure Acceptance Profile")
        verbose_name_plural = _("Secure Acceptance Profiles")

    @classmethod
    def get_profile(cls, hostname: str) -> Self:
        # Lambda function to get profiles whilst catching cryptography exceptions (in-case the Fernet key
        # unexpectedly changed, the data somehow got corrupted, etc).
        def _get_safe(**filters: str | bool) -> Self | None:
            try:
                return cls.objects.filter(**filters).first()
            except InvalidToken:
                logger.exception(
                    "Caught InvalidToken exception while retrieving profile"
                )
                return None

        # Try to get the profile for the given hostname
        profile = _get_safe(hostname__iexact=hostname)
        if profile:
            return profile

        # Fall back to the default profile
        profile = _get_safe(is_default=True)
        if profile:
            return profile

        # No default profile exists, so try and get something out of settings.
        if cyb_settings.PROFILE and cyb_settings.ACCESS and cyb_settings.SECRET:
            profile = cls()
            profile.hostname = ""
            profile.profile_id = cyb_settings.PROFILE
            profile.access_key = cyb_settings.ACCESS
            profile.secret_key = cyb_settings.SECRET
            profile.is_default = True
            profile.save()
            logger.info(
                "Created SecureAcceptanceProfile from Django settings: {}".format(
                    profile
                )
            )
            return profile

        # Out of options—raise an exception.
        raise cls.DoesNotExist()

    def save(self, *args: Any, **kwargs: Any) -> None:
        if self.is_default:
            self.__class__._default_manager.filter(is_default=True).update(
                is_default=False
            )
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return _(
            "Secure Acceptance Profile hostname=%(hostname)s, profile_id=%(profile_id)s"
        ) % dict(hostname=self.hostname, profile_id=self.profile_id)


class CyberSourceReply(models.Model):
    # Reply Metadata
    user = models.ForeignKey(
        AUTH_USER_MODEL,
        related_name="cybersource_replies",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    order = models.ForeignKey(
        "order.Order",
        related_name="cybersource_replies",
        null=True,
        on_delete=models.SET_NULL,
    )

    # Denotes what kind of response this is: Secure Acceptance or SOAP
    reply_type = models.SmallIntegerField(
        choices=CyberSourceReplyType.choices,
        default=CyberSourceReplyType.SA,
    )

    # Full Log of the reply data (raw data, so formats will differ between SA and SOAP replies)
    data = HStoreField()

    # More normalized view of the above reply data
    auth_avs_code = NullCharField(max_length=20, null=True)
    auth_code = NullCharField(max_length=20, null=True)
    auth_response = NullCharField(max_length=20, null=True)
    auth_trans_ref_no = NullCharField(max_length=128, null=True)
    decision = NullCharField(max_length=20, null=True)
    message = NullCharField(max_length=100, null=True)
    reason_code = models.IntegerField(null=True)
    req_bill_to_address_postal_code = NullCharField(max_length=64, null=True)
    req_bill_to_forename = NullCharField(max_length=255, null=True)
    req_bill_to_surname = NullCharField(max_length=255, null=True)
    req_card_expiry_date = NullCharField(max_length=10, null=True)
    req_reference_number = NullCharField(max_length=128, null=True)
    req_transaction_type = NullCharField(max_length=20, null=True)
    req_transaction_uuid = NullCharField(max_length=40, null=True)
    request_token = NullCharField(max_length=200, null=True)
    transaction_id = NullCharField(max_length=64, null=True)

    # Timestamps
    date_modified = models.DateTimeField(_("Date Modified"), auto_now=True)
    date_created = models.DateTimeField(_("Date Received"), auto_now_add=True)

    class Meta(TypedModelMeta):
        verbose_name = _("CyberSource Reply")
        verbose_name_plural = _("CyberSource Replies")
        ordering = ("date_created",)

    @classmethod
    def log_secure_acceptance_response(
        cls,
        order: Order,
        request: Request,
    ) -> Self:
        log = cls(
            user=request.user if request and request.user.is_authenticated else None,
            order=order,
            data=request.data,
            reply_type=CyberSourceReplyType.SA,
            auth_avs_code=request.data.get("auth_avs_code"),
            auth_code=request.data.get("auth_code"),
            auth_response=request.data.get("auth_response"),
            auth_trans_ref_no=request.data.get("auth_trans_ref_no"),
            decision=request.data.get("decision"),
            message=request.data.get("message"),
            reason_code=request.data.get("reason_code"),
            req_bill_to_address_postal_code=request.data.get(
                "req_bill_to_address_postal_code"
            ),
            req_bill_to_forename=request.data.get("req_bill_to_forename"),
            req_bill_to_surname=request.data.get("req_bill_to_surname"),
            req_card_expiry_date=request.data.get("req_card_expiry_date"),
            req_reference_number=request.data.get("req_reference_number"),
            req_transaction_type=request.data.get("req_transaction_type"),
            req_transaction_uuid=request.data.get("req_transaction_uuid"),
            request_token=request.data.get("request_token"),
            transaction_id=request.data.get("transaction_id"),
        )
        log.save()
        return log

    @classmethod
    def log_soap_response(
        cls,
        order: Order,
        response: SoapResponse,
        request: HttpRequest | None = None,
        card_expiry_date: str | None = None,
    ) -> Self:
        reply_data = zeepobj_to_dict(response)
        user = request.user if request and request.user.is_authenticated else None
        req_transaction_type = None
        if getattr(response, "paySubscriptionCreateReply", None):
            req_transaction_type = "create_payment_token"
        elif getattr(response, "ccCaptureReply", None):
            req_transaction_type = "capture"
        else:
            req_transaction_type = "authorization"
        baddr = order.billing_address
        log = cls(
            user=user,
            order=order,
            reply_type=CyberSourceReplyType.SOAP,
            data=reply_data,
            decision=response.decision,
            message=None,
            reason_code=response.reasonCode,
            req_bill_to_address_postal_code=None if baddr is None else baddr.postcode,
            req_bill_to_forename=None if baddr is None else baddr.first_name,
            req_bill_to_surname=None if baddr is None else baddr.last_name,
            req_card_expiry_date=card_expiry_date,
            req_reference_number=(
                response.merchantReferenceCode
                if "merchantReferenceCode" in response
                else None
            ),
            req_transaction_type=req_transaction_type,
            req_transaction_uuid=None,
            request_token=response.requestToken,
            transaction_id=response.requestID,
        )
        # These fields may or may not be present
        cc_auth_reply = getattr(response, "ccAuthReply", None)
        if cc_auth_reply:
            log.auth_code = getattr(cc_auth_reply, "authorizationCode", None)
            log.auth_response = getattr(cc_auth_reply, "processorResponse", None)
            log.auth_trans_ref_no = getattr(cc_auth_reply, "reconciliationID", None)
            log.auth_avs_code = getattr(cc_auth_reply, "avsCode", None)
        # Save and return log object
        log.save()

        return log

    def __str__(self) -> str:
        return _("CyberSource Reply %(created)s") % dict(created=self.date_created)

    @property
    def signed_date_time(self) -> datetime:
        try:
            return dateutil.parser.parse(self.data["signed_date_time"])
        except (AttributeError, ValueError, KeyError):
            return self.date_created

    def get_decision(self) -> Decision:
        # Accept
        if self.reason_code in (100,):
            return Decision.ACCEPT

        # Review
        if self.reason_code in (480,):
            return Decision.REVIEW

        # Rejections
        if self.reason_code in (
            110,
            200,
            201,
            202,
            203,
            204,
            205,
            207,
            208,
            210,
            211,
            221,
            222,
            230,
            231,
            232,
            233,
            234,
            400,
            481,
            520,
        ):
            return Decision.DECLINE

        # Errors
        if self.reason_code in (101, 102, 104, 150, 151, 152, 236, 240):
            return Decision.ERROR

        # If we don't recognize the reason code, go by the decision field
        if self.decision in (
            Decision.ACCEPT,
            Decision.REVIEW,
            Decision.DECLINE,
            Decision.ERROR,
        ):
            return self.decision

        # Last ditch catch-all
        return Decision.ERROR


class PaymentToken(models.Model):
    TYPES = {
        "001": "Visa",
        "002": "MasterCard",
        "003": "Amex",
        "004": "Discover",
        "005": "DINERS_CLUB",
        "006": "CARTE_BLANCHE",
        "007": "JCB",
        "014": "ENROUTE",
        "021": "JAL",
        "024": "MAESTRO_UK_DOMESTIC",
        "031": "DELTA",
        "033": "VISA_ELECTRON",
        "034": "DANKORT",
        "036": "CARTE_BLEUE",
        "037": "CARTA_SI",
        "042": "MAESTRO_INTERNATIONAL",
        "043": "GE_MONEY_UK_CARD",
        "050": "HIPERCARD",
        "054": "ELO",
    }

    log = models.ForeignKey(
        CyberSourceReply,
        related_name="tokens",
        on_delete=models.CASCADE,
    )
    token = models.CharField(max_length=100, unique=True)
    masked_card_number = models.CharField(max_length=25)
    card_type = models.CharField(max_length=10)

    class Meta(TypedModelMeta):
        verbose_name = _("Payment Token")
        verbose_name_plural = _("Payment Token")

    def log_field(self, key: str, default: str = "") -> str:
        return self.log.data.get(key, default)

    @property
    def card_type_name(self) -> str | None:
        return self.TYPES.get(self.card_type)

    @property
    def billing_zip_code(self) -> str | None:
        return self.log.req_bill_to_address_postal_code

    @property
    def expiry_month(self) -> str | None:
        if not self.log.req_card_expiry_date:
            return None
        return self.log.req_card_expiry_date.split("-")[0]

    @property
    def expiry_year(self) -> str | None:
        if not self.log.req_card_expiry_date:
            return None
        return self.log.req_card_expiry_date.split("-")[1]

    @property
    def card_last4(self) -> str:
        return self.masked_card_number[-4:]

    @property
    def card_holder(self) -> str:
        return "{} {}".format(
            self.log.req_bill_to_forename, self.log.req_bill_to_surname
        )

    def __str__(self) -> str:
        return "%s" % self.masked_card_number


class TransactionMixin(AbstractTransaction):
    log = models.ForeignKey(
        CyberSourceReply,
        related_name="transactions",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    token = models.ForeignKey(
        PaymentToken,
        related_name="transactions",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    authorization = models.ForeignKey(
        "self",
        related_name="captures",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        limit_choices_to={
            "txn_type": AbstractTransaction.AUTHORISE,
        },
        help_text=_(
            "For capture (debit) transactions, link to the authorization "
            "transaction that allowed the capture to take place."
        ),
    )
    request_token = models.CharField(max_length=200, null=True, blank=True)
    processed_datetime = models.DateTimeField(default=timezone.now)

    # Have to manually type hint reverse accessors
    captures: QuerySet[AbstractTransaction]

    class Meta(TypedModelMeta):
        abstract = True
        constraints = [
            CheckConstraint(
                check=(
                    Q(txn_type=AbstractTransaction.DEBIT)
                    | Q(authorization__isnull=True)
                ),
                name="only_captures_have_auths",
            ),
        ]

    def log_field(self, key: str, default: str = "") -> str:
        if self.log is None:
            return default
        return self.log.data.get(key, default)

    @property
    def is_pending_review(self) -> bool:
        return self.status == Decision.REVIEW

    @property
    def is_accepted_authorization(
        self,
    ) -> tuple[Literal[True], None] | tuple[Literal[False], StrOrPromise]:
        """
        Check if this transaction is an successfully approved Cybersource authorization.
        Returns a tuple, either ``(True, None)`` or ``(False, "Reason")``.
        """
        source_type = self.source.source_type
        if source_type.name != cyb_settings.SOURCE_TYPE:
            return False, (
                _("transaction has source {has}, expected {expected}").format(
                    has=source_type.name,
                    expected=cyb_settings.SOURCE_TYPE,
                )
            )
        if self.txn_type != AbstractTransaction.AUTHORISE:
            return False, (
                _("transaction has type {has}, expected {expected}").format(
                    has=self.txn_type,
                    expected=AbstractTransaction.AUTHORISE,
                )
            )
        if self.status != Decision.ACCEPT:
            return False, (
                _("transaction has status {has}, expected {expected}").format(
                    has=self.status,
                    expected=Decision.ACCEPT,
                )
            )
        return True, None

    @property
    def can_be_captured(
        self,
    ) -> tuple[Literal[True], None] | tuple[Literal[False], StrOrPromise]:
        """
        Check if this transaction can be captured by Cybersource.
        Returns a tuple, either ``(True, None)`` or ``(False, "Reason")``.
        """
        is_good_auth, err_reason = self.is_accepted_authorization
        if not is_good_auth:
            return False, cast(StrOrPromise, err_reason)
        # Need payment token to capture
        payment_token = self.token
        if payment_token is None:
            return False, _("transaction does not have a related payment token")
        # Check if there's any money left to capture
        remaining_capture_amount = self.get_remaining_amount_to_capture()
        if remaining_capture_amount <= 0:
            return False, _("transaction has already been fully captured")
        # Looks like we can capture this.
        return True, None

    def list_successful_captures(self) -> QuerySet[AbstractTransaction]:
        if not self.is_accepted_authorization:
            return self.captures.none()
        return self.captures.filter(
            txn_type=AbstractTransaction.DEBIT,
            status=Decision.ACCEPT,
        )

    def get_total_captured_amount(self) -> Decimal:
        if not self.is_accepted_authorization:
            return ZERO
        data = self.list_successful_captures().aggregate(total_amount=Sum("amount"))
        if data["total_amount"] is None:
            return ZERO
        return data["total_amount"]

    def get_remaining_amount_to_capture(self) -> Decimal:
        if not self.is_accepted_authorization:
            return ZERO
        total_captured = self.get_total_captured_amount()
        remaining = self.amount - total_captured
        return remaining
