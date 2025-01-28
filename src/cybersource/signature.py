from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING
import base64
import hashlib
import hmac

from django.core.exceptions import SuspiciousOperation

if TYPE_CHECKING:
    from django.http import HttpRequest


class SecureAcceptanceSigner:
    def __init__(self, secret_key: str) -> None:
        self.secret_key = secret_key

    def sign(
        self,
        data: Mapping[str, str | tuple[str]],
        signed_fields: Sequence[str] | set[str],
    ) -> bytes:
        key = self.secret_key.encode("utf-8")
        msg_raw = self._build_message(data, signed_fields).encode("utf-8")
        msg_hmac = hmac.new(key, msg_raw, hashlib.sha256)
        return base64.b64encode(msg_hmac.digest())

    def verify_request(self, request: HttpRequest) -> bool:
        # Ensure the signature is valid and that this request can be trusted
        signed_field_names_str = request.POST.get("signed_field_names")
        if not signed_field_names_str:
            raise SuspiciousOperation("Request has no fields to verify")
        signed_field_names = signed_field_names_str.split(",")
        signature_given = request.POST["signature"].encode("utf-8")
        signature_calc = self.sign(request.POST, signed_field_names)
        return signature_given == signature_calc

    def _build_message(
        self,
        data: Mapping[str, str | tuple[str]],
        signed_fields: Sequence[str] | set[str],
    ) -> str:
        parts = []
        for field in signed_fields:
            parts.append("%s=%s" % (field, data.get(field, "")))
        return ",".join(parts)
