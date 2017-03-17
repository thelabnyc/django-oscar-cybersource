from django.core.exceptions import SuspiciousOperation
from . import settings
import hashlib
import hmac
import base64


class SecureAcceptanceSigner(object):
    secret_key = settings.SECRET

    def sign(self, data, signed_fields):
        key = self.secret_key.encode('utf-8')
        msg_raw = self._build_message(data, signed_fields).encode('utf-8')
        msg_hmac = hmac.new(key, msg_raw, hashlib.sha256)
        return base64.b64encode(msg_hmac.digest())

    def verify_request(self, request):
        # Ensure the signature is valid and that this request can be trusted
        signed_field_names = request.POST.get('signed_field_names')
        if not signed_field_names:
            raise SuspiciousOperation("Request has no fields to verify")
        signed_field_names = signed_field_names.split(',')
        signature_given = request.POST['signature'].encode('utf-8')
        signature_calc = self.sign(request.POST, signed_field_names)
        return (signature_given == signature_calc)

    def _build_message(self, data, signed_fields):
        parts = []
        for field in signed_fields:
            parts.append( '%s=%s' % (field, data.get(field, '')) )
        return ','.join(parts)
