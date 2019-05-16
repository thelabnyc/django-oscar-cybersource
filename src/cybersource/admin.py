from django.contrib import admin
from django.utils.safestring import mark_safe
from . import models
import json


def format_json_for_display(data, width='auto'):
    """Use Pygments to pretty-print the JSON data field"""
    json_data = json.dumps(data, sort_keys=True, indent=4)
    try:
        from pygments import highlight
        from pygments.lexers import JsonLexer
        from pygments.formatters import HtmlFormatter
    except ImportError:
        return json_data
    prestyles = (
        'width: {};'
        'white-space: pre-wrap;'
        'word-wrap: break-word;'
    ).format(width)
    formatter = HtmlFormatter(style='colorful', prestyles=prestyles)
    response = highlight(json_data, JsonLexer(), formatter)
    style = "<style>" + formatter.get_style_defs() + "</style>"
    return mark_safe(style + response)


@admin.register(models.PaymentToken)
class PaymentTokenAdmin(admin.ModelAdmin):
    list_filter = ['card_type', 'log__date_created']
    search_fields = ['token', 'card_type', 'masked_card_number']
    fields = ['token', 'card_type', 'masked_card_number', 'log']
    list_display = ['token', 'card_type', 'masked_card_number', 'log']
    readonly_fields = fields


@admin.register(models.CyberSourceReply)
class CyberSourceReplyAdmin(admin.ModelAdmin):
    search_fields = [
        'order__number',
        'transaction_id',
        'message',
        'req_bill_to_address_postal_code',
        'req_bill_to_forename',
        'req_bill_to_surname',
    ]
    list_filter = ['reply_type', 'decision', 'reason_code', 'date_modified', 'date_created']
    list_display = [
        'id',
        'transaction_id',
        'req_bill_to_forename',
        'req_bill_to_surname',
        'user',
        'order',
        'reply_type',
        'req_transaction_type',
        'decision',
        'reason_code',
        'date_created',
        'date_modified',
    ]
    fields = [
        'user',
        'order',
        'reply_type',
        'auth_avs_code',
        'auth_code',
        'auth_response',
        'auth_trans_ref_no',
        'decision',
        'message',
        'reason_code',
        'req_bill_to_address_postal_code',
        'req_bill_to_forename',
        'req_bill_to_surname',
        'req_card_expiry_date',
        'req_reference_number',
        'req_transaction_type',
        'req_transaction_uuid',
        'request_token',
        'transaction_id',
        'formatted_data',
        'date_modified',
        'date_created',
    ]
    readonly_fields = fields

    def formatted_data(self, instance):
        return format_json_for_display(instance.data)
    formatted_data.short_description = 'Reply Data'


@admin.register(models.SecureAcceptanceProfile)
class SecureAcceptanceProfileAdmin(admin.ModelAdmin):
    list_display = ['id', 'hostname', 'profile_id', 'is_default']
    fields = ['hostname', 'profile_id', 'access_key', 'secret_key', 'is_default']
