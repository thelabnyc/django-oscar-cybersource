from __future__ import annotations

from typing import TYPE_CHECKING, Any
import json

from django.utils.encoding import force_bytes, force_str
from django.utils.safestring import mark_safe
from thelabdb.fields import EncryptedTextField

if TYPE_CHECKING:
    from django.utils.safestring import SafeString


def format_json_for_display(data: Any, width: str = "auto") -> str | SafeString:
    """Use Pygments to pretty-print the JSON data field"""
    json_data = json.dumps(data, sort_keys=True, indent=4)
    try:
        from pygments import highlight
        from pygments.formatters import HtmlFormatter
        from pygments.lexers import JsonLexer
    except ImportError:
        return json_data
    prestyles = ("width: {};" "white-space: pre-wrap;" "word-wrap: break-word;").format(
        width
    )
    formatter = HtmlFormatter(style="colorful", prestyles=prestyles)
    response = highlight(json_data, JsonLexer(), formatter)
    style = "<style>" + formatter.get_style_defs() + "</style>"
    return mark_safe(style + response)


def encrypt_session_id(session_id: str) -> str:
    fernet = EncryptedTextField().fernet
    session_id_bytes = force_bytes(session_id)
    encrypted_bytes = fernet.encrypt(session_id_bytes)
    encrypted_str = force_str(encrypted_bytes)
    return encrypted_str


def decrypt_session_id(encrypted_str: str) -> str:
    fernet = EncryptedTextField().fernet
    encrypted_bytes = force_bytes(encrypted_str)
    session_id_bytes = fernet.decrypt(encrypted_bytes)
    session_id = force_str(session_id_bytes)
    return session_id
