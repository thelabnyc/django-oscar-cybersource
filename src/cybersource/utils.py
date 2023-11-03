from django.utils.safestring import mark_safe
from django.utils.encoding import force_bytes, force_str
from thelabdb.fields import EncryptedTextField
from suds import sudsobject
import json


def format_json_for_display(data, width="auto"):
    """Use Pygments to pretty-print the JSON data field"""
    json_data = json.dumps(data, sort_keys=True, indent=4)
    try:
        from pygments import highlight
        from pygments.lexers import JsonLexer
        from pygments.formatters import HtmlFormatter
    except ImportError:
        return json_data
    prestyles = ("width: {};" "white-space: pre-wrap;" "word-wrap: break-word;").format(
        width
    )
    formatter = HtmlFormatter(style="colorful", prestyles=prestyles)
    response = highlight(json_data, JsonLexer(), formatter)
    style = "<style>" + formatter.get_style_defs() + "</style>"
    return mark_safe(style + response)


def sudsobj_to_dict(sudsobj, key_prefix=""):
    """Convert Suds object into a flattened dictionary"""
    out = {}
    # Handle lists
    if isinstance(sudsobj, list):
        for i, child in enumerate(sudsobj):
            child_key = "{}[{}]".format(key_prefix, i)
            out.update(sudsobj_to_dict(child, key_prefix=child_key))
        return out
    # Handle Primitives
    if not hasattr(sudsobj, "__keylist__"):
        out[key_prefix] = sudsobj
        return out
    # Handle Suds Objects
    for parent_key, parent_val in sudsobject.asdict(sudsobj).items():
        full_parent_key = (
            "{}.{}".format(key_prefix, parent_key) if key_prefix else parent_key
        )
        out.update(sudsobj_to_dict(parent_val, key_prefix=full_parent_key))
    return out


def encrypt_session_id(session_id):
    fernet = EncryptedTextField().fernet
    session_id_bytes = force_bytes(session_id)
    encrypted_bytes = fernet.encrypt(session_id_bytes)
    encrypted_str = force_str(encrypted_bytes)
    return encrypted_str


def decrypt_session_id(encrypted_str):
    fernet = EncryptedTextField().fernet
    encrypted_bytes = force_bytes(encrypted_str)
    session_id_bytes = fernet.decrypt(encrypted_bytes)
    session_id = force_str(session_id_bytes)
    return session_id
