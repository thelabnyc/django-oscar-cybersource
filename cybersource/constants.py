from decimal import Decimal
from enum import StrEnum, unique

from django.db.models import IntegerChoices
from django.utils.translation import gettext_lazy as _

CHECKOUT_ORDER_ID = "checkout_order_id"
CHECKOUT_FINGERPRINT_SESSION_ID = "cybersource_fingerprint_session_id"


@unique
class Decision(StrEnum):
    ACCEPT = "ACCEPT"
    REVIEW = "REVIEW"
    DECLINE = "DECLINE"
    ERROR = "ERROR"


class CyberSourceReplyType(IntegerChoices):
    SA = 1, _("Secure Acceptance")
    SOAP = 2, _("SOAP API")


# TERMINAL_DESCRIPTOR = base64.b64encode(b"bluefin")
TERMINAL_DESCRIPTOR = "Ymx1ZWZpbg=="

# Used for quantizing decimals
PRECISION = Decimal("0.01")

ZERO = Decimal("0.00")
