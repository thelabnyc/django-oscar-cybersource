from collections.abc import Mapping, Sequence
from typing import Any, Optional

from django.conf import settings as djsettings
from django.core.signals import setting_changed
from django.dispatch import receiver
from django.utils.translation import gettext_noop
from pydantic import Base64Bytes, BaseModel, ConfigDict, HttpUrl


class CybersourceSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    # Secure Acceptance
    PROFILE: Optional[str]
    ACCESS: Optional[str]
    SECRET: Optional[str]

    # SOAP API
    ORG_ID: str
    MERCHANT_ID: str
    WSDL: HttpUrl
    PKCS12_DATA: Base64Bytes
    PKCS12_PASSWORD: Base64Bytes

    # Checkout URL flow
    REDIRECT_PENDING: str
    REDIRECT_SUCCESS: str
    REDIRECT_FAIL: str
    ENDPOINT_PAY: HttpUrl

    # Formatting
    DATE_FORMAT: str
    LOCALE: str

    # Checkout device fingerprinting
    FINGERPRINT_PROTOCOL: str
    FINGERPRINT_HOST: str

    # Misc
    SOURCE_TYPE: str
    DEFAULT_CURRENCY: str
    DECISION_MANAGER_KEYS: Sequence[str]
    SHIPPING_METHOD_DEFAULT: str
    SHIPPING_METHOD_MAPPING: Mapping[str, str]


def load(raw_settings: Mapping[str, Any]) -> CybersourceSettings:
    return CybersourceSettings.model_validate(raw_settings)


def _get_raw_config() -> Mapping[str, Any]:
    _defaults = {
        "WSDL": "https://ics2wstesta.ic3.com/commerce/1.x/transactionProcessor/CyberSourceTransaction_1.155.wsdl",
        "ENDPOINT_PAY": "https://testsecureacceptance.cybersource.com/silent/pay",
        "DATE_FORMAT": "%Y-%m-%dT%H:%M:%SZ",
        "LOCALE": "en",
        "FINGERPRINT_PROTOCOL": "https",
        "FINGERPRINT_HOST": "h.online-metrix.net",
        "SOURCE_TYPE": gettext_noop("Cybersource Secure Acceptance"),
        "DEFAULT_CURRENCY": djsettings.OSCAR_DEFAULT_CURRENCY,
        "DECISION_MANAGER_KEYS": [],
        "SHIPPING_METHOD_DEFAULT": "none",
        "SHIPPING_METHOD_MAPPING": {},
    }

    # Fetch new-style config from the `CYBERSOURCE` dict in Django settings
    _raw_new = {}
    if hasattr(djsettings, "CYBERSOURCE"):
        _raw_new = djsettings.CYBERSOURCE

    # Fallback to old config version (separate values in Django settings)
    keys = [
        "PROFILE",
        "ACCESS",
        "SECRET",
        "ORG_ID",
        "MERCHANT_ID",
        "PKCS12_DATA",
        "PKCS12_PASSWORD",
        "WSDL",
        "REDIRECT_PENDING",
        "REDIRECT_SUCCESS",
        "REDIRECT_FAIL",
        "ENDPOINT_PAY",
        "DATE_FORMAT",
        "LOCALE",
        "FINGERPRINT_PROTOCOL",
        "FINGERPRINT_HOST",
        "SOURCE_TYPE",
        "DECISION_MANAGER_KEYS",
        "SHIPPING_METHOD_DEFAULT",
        "SHIPPING_METHOD_MAPPING",
    ]
    _raw_legacy = {
        k: v
        for k, v in [
            (key, getattr(djsettings, f"CYBERSOURCE_{key}", None)) for key in keys
        ]
        if v is not None
    }

    # Combine and validate
    return _defaults | _raw_legacy | _raw_new


settings = load(_get_raw_config())


@receiver(setting_changed)
def on_setting_changed(*args: Any, **kwargs: Any) -> None:
    # Update the settings object values
    config = _get_raw_config()
    settings.__dict__ = load(config).__dict__
