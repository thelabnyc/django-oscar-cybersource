from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def overridable(name, default=None, required=False):
    if required:
        if not hasattr(settings, name) or not getattr(settings, name):
            raise ImproperlyConfigured("%s must be defined in Django settings" % name)
    return getattr(settings, name, default)


DEFAULT_CURRENCY = overridable('OSCAR_DEFAULT_CURRENCY', required=True)

PROFILE = overridable('CYBERSOURCE_PROFILE', required=True)
ACCESS = overridable('CYBERSOURCE_ACCESS', required=True)
SECRET = overridable('CYBERSOURCE_SECRET', required=True)

ORG_ID = overridable('CYBERSOURCE_ORG_ID', required=True)
MERCHANT_ID = overridable('CYBERSOURCE_MERCHANT_ID', required=True)

REDIRECT_PENDING = overridable('CYBERSOURCE_REDIRECT_PENDING', required=True)
REDIRECT_SUCCESS = overridable('CYBERSOURCE_REDIRECT_SUCCESS', required=True)
REDIRECT_FAIL = overridable('CYBERSOURCE_REDIRECT_FAIL', required=True)

ENDPOINT_PAY = overridable('CYBERSOURCE_ENDPOINT_PAY', 'https://testsecureacceptance.cybersource.com/silent/pay')

DATE_FORMAT = overridable('CYBERSOURCE_DATE_FORMAT', '%Y-%m-%dT%H:%M:%SZ')
LOCALE = overridable('CYBERSOURCE_LOCALE', 'en')

FINGERPRINT_PROTOCOL = overridable('CYBERSOURCE_FINGERPRINT_PROTOCOL', 'https')
FINGERPRINT_HOST = overridable('CYBERSOURCE_FINGERPRINT_HOST', 'h.online-metrix.net')

SOURCE_TYPE = overridable('CYBERSOURCE_SOURCE_TYPE', 'Cybersource Secure Acceptance')
CARD_REJECT_ERROR = overridable('CYBERSOURCE_CARD_REJECT_ERROR', 'Card was declined by the issuing bank. Please try a different card.')
