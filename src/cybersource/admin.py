from django.contrib import admin
from django.utils.safestring import SafeString

from . import models
from .utils import format_json_for_display


@admin.register(models.PaymentToken)
class PaymentTokenAdmin(admin.ModelAdmin[models.PaymentToken]):
    list_filter = ["card_type", "log__date_created"]
    search_fields = ["token", "card_type", "masked_card_number"]
    fields = ["token", "card_type", "masked_card_number", "log"]
    list_display = ["token", "card_type", "masked_card_number", "log"]
    readonly_fields = fields  # type:ignore[assignment]


@admin.register(models.CyberSourceReply)
class CyberSourceReplyAdmin(admin.ModelAdmin[models.CyberSourceReply]):
    search_fields = [
        "order__number",
        "transaction_id",
        "message",
        "req_bill_to_address_postal_code",
        "req_bill_to_forename",
        "req_bill_to_surname",
    ]
    list_filter = [
        "reply_type",
        "decision",
        "reason_code",
        "date_modified",
        "date_created",
    ]
    list_display = [
        "id",
        "transaction_id",
        "req_bill_to_forename",
        "req_bill_to_surname",
        "user",
        "order",
        "reply_type",
        "req_transaction_type",
        "decision",
        "reason_code",
        "date_created",
        "date_modified",
    ]
    fields = [
        "user",
        "order",
        "reply_type",
        "auth_avs_code",
        "auth_code",
        "auth_response",
        "auth_trans_ref_no",
        "decision",
        "message",
        "reason_code",
        "req_bill_to_address_postal_code",
        "req_bill_to_forename",
        "req_bill_to_surname",
        "req_card_expiry_date",
        "req_reference_number",
        "req_transaction_type",
        "req_transaction_uuid",
        "request_token",
        "transaction_id",
        "formatted_data",
        "date_modified",
        "date_created",
    ]
    readonly_fields = fields  # type:ignore[assignment]

    def formatted_data(self, instance: models.CyberSourceReply) -> str | SafeString:
        return format_json_for_display(instance.data)

    formatted_data.short_description = "Reply Data"  # type:ignore[attr-defined]


@admin.register(models.SecureAcceptanceProfile)
class SecureAcceptanceProfileAdmin(admin.ModelAdmin[models.SecureAcceptanceProfile]):
    list_display = ["id", "hostname", "profile_id", "is_default"]
    fields = ["hostname", "profile_id", "access_key", "secret_key", "is_default"]
