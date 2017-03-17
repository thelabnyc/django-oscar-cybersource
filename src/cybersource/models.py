from datetime import datetime
from django.db import models
from django.contrib.postgres.fields import HStoreField
from oscar.core.compat import AUTH_USER_MODEL
from .constants import DECISION_REVIEW
import dateutil.parser


class CyberSourceReply(models.Model):
    user = models.ForeignKey(AUTH_USER_MODEL,
        related_name='cybersource_replies', null=True, blank=True, on_delete=models.SET_NULL)
    order = models.ForeignKey('order.Order', related_name='cybersource_replies', null=True, on_delete=models.SET_NULL)
    data = HStoreField()
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
        except (AttributeError, ValueError):
            return None


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

    log = models.ForeignKey(CyberSourceReply, related_name='tokens')
    token = models.CharField(max_length=100, unique=True)
    masked_card_number = models.CharField(max_length=25)
    card_type = models.CharField(max_length=10)

    @property
    def card_type_name(self):
        return self.TYPES.get(self.card_type)

    @property
    def billing_zip_code(self):
        return self.log_field('req_bill_to_address_postal_code')

    @property
    def expiry_month(self):
        return self.log_field('req_card_expiry_date').split('-')[0]

    @property
    def expiry_year(self):
        return self.log_field('req_card_expiry_date').split('-')[1]

    @property
    def card_last4(self):
        return self.masked_card_number[-4:]

    @property
    def card_holder(self):
        return "%s %s" % (self.log_field('req_bill_to_forename'), self.log_field('req_bill_to_surname'))

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
