from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
import warnings


def overridable(name, default=None, required=False):
    if required:
        if not hasattr(settings, name) or not getattr(settings, name):
            raise ImproperlyConfigured("%s must be defined in Django settings" % name)
    return getattr(settings, name, default)


DEFAULT_CURRENCY = overridable('OSCAR_DEFAULT_CURRENCY', required=True)

PROFILE = overridable('CYBERSOURCE_PROFILE')
ACCESS = overridable('CYBERSOURCE_ACCESS')
SECRET = overridable('CYBERSOURCE_SECRET')
if PROFILE:
    warnings.warn('CYBERSOURCE_PROFILE setting is deprecated. Use cybersource.SecureAcceptanceProfile model instead.', DeprecationWarning)
if ACCESS:
    warnings.warn('CYBERSOURCE_ACCESS setting is deprecated. Use cybersource.SecureAcceptanceProfile model instead.', DeprecationWarning)
if SECRET:
    warnings.warn('CYBERSOURCE_SECRET setting is deprecated. Use cybersource.SecureAcceptanceProfile model instead.', DeprecationWarning)

ORG_ID = overridable('CYBERSOURCE_ORG_ID', required=True)
MERCHANT_ID = overridable('CYBERSOURCE_MERCHANT_ID', 'tempurdrcyb', required=True)
CYBERSOURCE_SOAP_KEY = overridable('CYBERSOURCE_SOAP_KEY',
                                   ('+zUgnDT8pbFgODXldYN6YCtU+I5QAtb0Qrb3tGQ/QaiSRLDgBDQ2NXxz64mF/IDrlQGlv87jHTATF/BKUN'
                                    'G7xcqCJnvA+yzDnoqXDkWwrXNgKRRCV/9sBv3xEh7woZXkPEvsV1ZFXA8axH7GgY9Bw6Yg2Kk9U57PINNe'
                                    'jy0D+9V8tDzq/7JfLlFad8La09uzaxZ8MhFiRQwTYNGyWOPVIY+rCrJ9lh6j+Ow00b9/Lz5TvAUIi7gKBK'
                                    'IykBQzoT6PQXqAwdRiVtJsG9V53jnEB9EC/TYXLqbbqIaX3x9WC0JDRORmnymOt4meh9RndjSDsA5ANGpE'
                                    'MCaV4E3u2nk60w=='), required=True)
CYBERSOURCE_WSDL = overridable('CYBERSOURCE_WSDL',
                               'https://ics2wstesta.ic3.com/commerce/1.x/transactionProcessor/CyberSourceTransaction_1.155.wsdl')

REDIRECT_PENDING = overridable('CYBERSOURCE_REDIRECT_PENDING', required=True)
REDIRECT_SUCCESS = overridable('CYBERSOURCE_REDIRECT_SUCCESS', required=True)
REDIRECT_FAIL = overridable('CYBERSOURCE_REDIRECT_FAIL', required=True)

ENDPOINT_PAY = overridable('CYBERSOURCE_ENDPOINT_PAY', 'https://testsecureacceptance.cybersource.com/silent/pay')

DATE_FORMAT = overridable('CYBERSOURCE_DATE_FORMAT', '%Y-%m-%dT%H:%M:%SZ')
LOCALE = overridable('CYBERSOURCE_LOCALE', 'en')

FINGERPRINT_PROTOCOL = overridable('CYBERSOURCE_FINGERPRINT_PROTOCOL', 'https')
FINGERPRINT_HOST = overridable('CYBERSOURCE_FINGERPRINT_HOST', 'h.online-metrix.net')

SOURCE_TYPE = overridable('CYBERSOURCE_SOURCE_TYPE', 'Cybersource Secure Acceptance')

DECISION_MANAGER_KEYS = overridable('CYBERSOURCE_DECISION_MANAGER_KEYS', [])

SHIPPING_METHOD_DEFAULT = overridable('CYBERSOURCE_SHIPPING_METHOD_DEFAULT', 'none')
SHIPPING_METHOD_MAPPING = overridable('CYBERSOURCE_SHIPPING_METHOD_MAPPING', {})
