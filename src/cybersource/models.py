from decimal import Decimal
from cryptography.fernet import InvalidToken
from django.conf import settings as django_settings
from django.db import models
from django.db.models import Q, CheckConstraint, Sum
from django.contrib.postgres.fields import HStoreField
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from oscar.core.compat import AUTH_USER_MODEL
from oscar.models.fields import NullCharField
from oscar.apps.payment.abstract_models import AbstractTransaction
from thelabdb.fields import EncryptedTextField
from .utils import sudsobj_to_dict
from .constants import (
    DECISION_ACCEPT,
    DECISION_REVIEW,
    DECISION_DECLINE,
    DECISION_ERROR,
)
from . import settings as cyb_settings
import dateutil.parser
import logging

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

    class Meta:
        verbose_name = _("Secure Acceptance Profile")
        verbose_name_plural = _("Secure Acceptance Profiles")

    @classmethod
    def get_profile(cls, hostname):
        # Lambda function to get profiles whilst catching cryptography exceptions (in-case the Fernet key
        # unexpectedly changed, the data somehow got corrupted, etc).
        def _get_safe(**filters):
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
        if (
            hasattr(django_settings, "CYBERSOURCE_PROFILE")
            and hasattr(django_settings, "CYBERSOURCE_ACCESS")
            and hasattr(django_settings, "CYBERSOURCE_SECRET")
        ):
            profile = SecureAcceptanceProfile()
            profile.hostname = ""
            profile.profile_id = django_settings.CYBERSOURCE_PROFILE
            profile.access_key = django_settings.CYBERSOURCE_ACCESS
            profile.secret_key = django_settings.CYBERSOURCE_SECRET
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

    def save(self, *args, **kwargs):
        if self.is_default:
            self.__class__._default_manager.filter(is_default=True).update(
                is_default=False
            )
        return super().save(*args, **kwargs)

    def __str__(self):
        return _(
            "Secure Acceptance Profile hostname=%(hostname)s, profile_id=%(profile_id)s"
        ) % dict(hostname=self.hostname, profile_id=self.profile_id)


class CyberSourceReply(models.Model):
    REPLY_TYPE_SA = 1
    REPLY_TYPE_SOAP = 2
    REPLY_TYPE_CHOICES = [
        (REPLY_TYPE_SA, _("Secure Acceptance")),
        (REPLY_TYPE_SOAP, _("SOAP API")),
    ]

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
        choices=REPLY_TYPE_CHOICES, default=REPLY_TYPE_SA
    )

    # Full Log of the reply data (raw data, so formats will differ between SA and SOAP replies)
    data = HStoreField()

    # More normalized view of the above reply data
    auth_avs_code = NullCharField(max_length=20)
    auth_code = NullCharField(max_length=20)
    auth_response = NullCharField(max_length=20)
    auth_trans_ref_no = NullCharField(max_length=128)
    decision = NullCharField(max_length=20)
    message = NullCharField(max_length=100)
    reason_code = models.IntegerField(null=True)
    req_bill_to_address_postal_code = NullCharField(max_length=64)
    req_bill_to_forename = NullCharField(max_length=255)
    req_bill_to_surname = NullCharField(max_length=255)
    req_card_expiry_date = NullCharField(max_length=10)
    req_reference_number = NullCharField(max_length=128)
    req_transaction_type = NullCharField(max_length=20)
    req_transaction_uuid = NullCharField(max_length=40)
    request_token = NullCharField(max_length=200)
    transaction_id = NullCharField(max_length=64)

    # Timestamps
    date_modified = models.DateTimeField(_("Date Modified"), auto_now=True)
    date_created = models.DateTimeField(_("Date Received"), auto_now_add=True)

    class Meta:
        verbose_name = _("CyberSource Reply")
        verbose_name_plural = _("CyberSource Replies")
        ordering = ("date_created",)

    @classmethod
    def log_secure_acceptance_response(cls, order, request):
        log = CyberSourceReply(
            user=request.user if request and request.user.is_authenticated else None,
            order=order,
            data=request.data,
            reply_type=CyberSourceReply.REPLY_TYPE_SA,
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
    def log_soap_response(cls, order, response, request=None, card_expiry_date=None):
        reply_data = sudsobj_to_dict(response)
        user = request.user if request and request.user.is_authenticated else None
        req_transaction_type = None
        if "paySubscriptionCreateReply" in response:
            req_transaction_type = "create_payment_token"
        elif "ccCaptureReply" in response:
            req_transaction_type = "capture"
        else:
            req_transaction_type = "authorization"
        log = CyberSourceReply(
            user=user,
            order=order,
            reply_type=CyberSourceReply.REPLY_TYPE_SOAP,
            data=reply_data,
            decision=response.decision,
            message=None,
            reason_code=response.reasonCode,
            req_bill_to_address_postal_code=order.billing_address.postcode,
            req_bill_to_forename=order.billing_address.first_name,
            req_bill_to_surname=order.billing_address.last_name,
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

    def __str__(self):
        return _("CyberSource Reply %(created)s") % dict(created=self.date_created)

    @property
    def signed_date_time(self):
        try:
            return dateutil.parser.parse(self.data["signed_date_time"])
        except (AttributeError, ValueError, KeyError):
            return self.date_created

    def get_decision(self):
        # Accept
        if self.reason_code in (100,):
            return DECISION_ACCEPT

        # Review
        if self.reason_code in (201, 480):
            return DECISION_REVIEW

        # Rejections
        if self.reason_code in (
            110,
            200,
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
            return DECISION_DECLINE

        # Errors
        if self.reason_code in (101, 102, 104, 150, 151, 152, 236, 240):
            return DECISION_ERROR

        # If we don't recognize the reason code, go by the decision field
        if self.decision in (
            DECISION_ACCEPT,
            DECISION_REVIEW,
            DECISION_DECLINE,
            DECISION_ERROR,
        ):
            return self.decision

        # Last ditch catch-all
        return DECISION_ERROR


class ReplyLogMixin(object):
    def log_field(self, key, default=""):
        return self.log.data.get(key, default)


class PaymentToken(ReplyLogMixin, models.Model):
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
        CyberSourceReply, related_name="tokens", on_delete=models.CASCADE
    )
    token = models.CharField(max_length=100, unique=True)
    masked_card_number = models.CharField(max_length=25)
    card_type = models.CharField(max_length=10)

    class Meta:
        verbose_name = _("Payment Token")
        verbose_name_plural = _("Payment Token")

    @property
    def card_type_name(self):
        return self.TYPES.get(self.card_type)

    @property
    def billing_zip_code(self):
        return self.log.req_bill_to_address_postal_code

    @property
    def expiry_month(self):
        if not self.log.req_card_expiry_date:
            return None
        return self.log.req_card_expiry_date.split("-")[0]

    @property
    def expiry_year(self):
        if not self.log.req_card_expiry_date:
            return None
        return self.log.req_card_expiry_date.split("-")[1]

    @property
    def card_last4(self):
        return self.masked_card_number[-4:]

    @property
    def card_holder(self):
        return "%s %s" % (self.log.req_bill_to_forename, self.log.req_bill_to_surname)

    def __str__(self):
        return "%s" % self.masked_card_number


class TransactionMixin(ReplyLogMixin, models.Model):
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

    class Meta:
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

    @property
    def is_pending_review(self):
        return self.status == DECISION_REVIEW

    @property
    def is_accepted_authorization(self):
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
        if self.status != DECISION_ACCEPT:
            return False, (
                _("transaction has status {has}, expected {expected}").format(
                    has=self.status,
                    expected=DECISION_ACCEPT,
                )
            )
        return True, None

    @property
    def can_be_captured(self):
        """
        Check if this transaction can be captured by Cybersource.
        Returns a tuple, either ``(True, None)`` or ``(False, "Reason")``.
        """
        is_good_auth, err_reason = self.is_accepted_authorization
        if not is_good_auth:
            return is_good_auth, err_reason
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

    def list_successful_captures(self):
        if not self.is_accepted_authorization:
            return self.captures.none()
        return self.captures.filter(
            txn_type=AbstractTransaction.DEBIT,
            status=DECISION_ACCEPT,
        )

    def get_total_captured_amount(self):
        if not self.is_accepted_authorization:
            return Decimal("0.00")
        data = self.list_successful_captures().aggregate(total_amount=Sum("amount"))
        if data["total_amount"] is None:
            return Decimal("0.00")
        return data["total_amount"]

    def get_remaining_amount_to_capture(self):
        if not self.is_accepted_authorization:
            return Decimal("0.00")
        total_captured = self.get_total_captured_amount()
        remaining = self.amount - total_captured
        return remaining
