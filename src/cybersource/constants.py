from decimal import Decimal

CHECKOUT_ORDER_ID = "checkout_order_id"
CHECKOUT_FINGERPRINT_SESSION_ID = "cybersource_fingerprint_session_id"

# Default code for the email to send after successful checkout
DECISION_ACCEPT = "ACCEPT"
DECISION_REVIEW = "REVIEW"
DECISION_DECLINE = "DECLINE"
DECISION_ERROR = "ERROR"

# TERMINAL_DESCRIPTOR = base64.b64encode(b"bluefin")
TERMINAL_DESCRIPTOR = "Ymx1ZWZpbg=="

# Used for quantizing decimals
PRECISION = Decimal("0.01")
