from cryptography.fernet import InvalidToken
from datetime import datetime
from django.conf import settings
from django.db import models
from django.contrib.postgres.fields import HStoreField
from oscar.core.compat import AUTH_USER_MODEL
from oscar.models.fields import NullCharField
from fernet_fields import EncryptedTextField
from .constants import DECISION_ACCEPT, DECISION_REVIEW, DECISION_DECLINE, DECISION_ERROR
import dateutil.parser
import logging

logger = logging.getLogger(__name__)


class SecureAcceptanceProfile(models.Model):
    hostname = models.CharField("Hostname", max_length=100, blank=True, unique=True,
        help_text="When the request matches this hostname, this profile will be used.")
    profile_id = models.CharField("Profile ID", max_length=50, unique=True)
    access_key = models.CharField("Access Key", max_length=50)
    secret_key = EncryptedTextField("Secret Key")
    is_default = models.BooleanField("Is Default Profile?", default=False,
        help_text="If no profile can be found for a request's hostname, the default profile will be used.")


    @classmethod
    def get_profile(cls, hostname):
        # Lambda function to get profiles whilst catching cryptography exceptions (in-case the Fernet key
        # unexpectedly changed, the data somehow got corrupted, etc).
        def _get_safe(**filters):
            try:
                return cls.objects.filter(**filters).first()
            except InvalidToken:
                logger.exception('Caught InvalidToken exception while retrieving profile')
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
        if hasattr(settings, 'CYBERSOURCE_PROFILE') and hasattr(settings, 'CYBERSOURCE_ACCESS') and hasattr(settings, 'CYBERSOURCE_SECRET'):
            profile = SecureAcceptanceProfile()
            profile.hostname = ''
            profile.profile_id = settings.CYBERSOURCE_PROFILE
            profile.access_key = settings.CYBERSOURCE_ACCESS
            profile.secret_key = settings.CYBERSOURCE_SECRET
            profile.is_default = True
            profile.save()
            logger.info('Created SecureAcceptanceProfile from Django settings: {}'.format(profile))
            return profile

        # Out of options—raise an exception.
        raise cls.DoesNotExist()


    def save(self, *args, **kwargs):
        if self.is_default:
            self.__class__._default_manager.filter(is_default=True).update(is_default=False)
        return super().save(*args, **kwargs)


    def __str__(self):
        return 'Secure Acceptance Profile hostname={}, profile_id={}'.format(self.hostname, self.profile_id)



class CyberSourceReply(models.Model):
    REPLY_TYPE_SA = 1
    REPLY_TYPE_SOAP = 2
    REPLY_TYPE_CHOICES = [
        (REPLY_TYPE_SA, "Secure Acceptance"),
        (REPLY_TYPE_SOAP, "SOAP API"),
    ]


    # Reply Metadata
    user = models.ForeignKey(AUTH_USER_MODEL,
        related_name='cybersource_replies', null=True, blank=True, on_delete=models.SET_NULL)
    order = models.ForeignKey('order.Order', related_name='cybersource_replies', null=True, on_delete=models.SET_NULL)

    # Denotes what kind of response this is: Secure Acceptance or SOAP
    reply_type = models.SmallIntegerField(
        choices=REPLY_TYPE_CHOICES,
        default=REPLY_TYPE_SA)

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
    date_modified = models.DateTimeField("Date Modified", auto_now=True)
    date_created = models.DateTimeField("Date Received", auto_now_add=True)

    class Meta:
        ordering = ('date_created', )

    def __str__(self):
        return 'CyberSource Reply %s' % self.date_created

    @property
    def signed_date_time(self):
        try:
            return dateutil.parser.parse(self.data['signed_date_time'])
        except (AttributeError, ValueError, KeyError):
            return self.date_created


    def get_decision(self):
        # Accept
        if self.reason_code in (100, ):
            return DECISION_ACCEPT

        # Review
        if self.reason_code in (201, 480):
            return DECISION_REVIEW

        # Rejections
        if self.reason_code in (110, 200, 202, 203, 204, 205, 207, 208, 210, 211, 221, 222, 230, 231, 232, 233, 234, 400, 481, 520):
            return DECISION_DECLINE

        # Errors
        if self.reason_code in (101, 102, 104, 150, 151, 152, 236, 240):
            return DECISION_ERROR

        # If we don't recognize the reason code, go by the decision field
        if self.decision in (DECISION_ACCEPT, DECISION_REVIEW, DECISION_DECLINE, DECISION_ERROR):
            return self.decision

        # Last ditch catch-all
        return DECISION_ERROR



class ReplyLogMixin(object):
    def log_field(self, key, default=''):
        return self.log.data.get(key, default)


class PaymentToken(ReplyLogMixin, models.Model):
    TYPES = {
        '001': 'Visa',
        '002': 'MasterCard',
        '003': 'Amex',
        '004': 'Discover',
        '005': 'DINERS_CLUB',
        '006': 'CARTE_BLANCHE',
        '007': 'JCB',
        '014': 'ENROUTE',
        '021': 'JAL',
        '024': 'MAESTRO_UK_DOMESTIC',
        '031': 'DELTA',
        '033': 'VISA_ELECTRON',
        '034': 'DANKORT',
        '036': 'CARTE_BLEUE',
        '037': 'CARTA_SI',
        '042': 'MAESTRO_INTERNATIONAL',
        '043': 'GE_MONEY_UK_CARD',
        '050': 'HIPERCARD',
        '054': 'ELO',
    }

    log = models.ForeignKey(CyberSourceReply, related_name='tokens', on_delete=models.CASCADE)
    token = models.CharField(max_length=100, unique=True)
    masked_card_number = models.CharField(max_length=25)
    card_type = models.CharField(max_length=10)

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
        return self.log.req_card_expiry_date.split('-')[0]

    @property
    def expiry_year(self):
        if not self.log.req_card_expiry_date:
            return None
        return self.log.req_card_expiry_date.split('-')[1]

    @property
    def card_last4(self):
        return self.masked_card_number[-4:]

    @property
    def card_holder(self):
        return "%s %s" % (self.log.req_bill_to_forename, self.log.req_bill_to_surname)

    def __str__(self):
        return "%s" % self.masked_card_number


class TransactionMixin(ReplyLogMixin, models.Model):
    log = models.ForeignKey(CyberSourceReply,
        related_name='transactions',
        null=True,
        blank=True,
        on_delete=models.SET_NULL)
    token = models.ForeignKey(PaymentToken,
        related_name='transactions',
        null=True,
        blank=True,
        on_delete=models.SET_NULL)
    request_token = models.CharField(max_length=200, null=True, blank=True)
    processed_datetime = models.DateTimeField(default=datetime.now)

    class Meta:
        abstract = True

    @property
    def is_pending_review(self):
        return self.status == DECISION_REVIEW
