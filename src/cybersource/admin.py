from django.contrib import admin
from . import models


@admin.register(models.PaymentToken)
class PaymentTokenAdmin(admin.ModelAdmin):
    list_filter = ['card_type', 'log__date_created']
    search_fields = ['token', 'card_type', 'masked_card_number']
    fields = ['token', 'card_type', 'masked_card_number', 'log']
    list_display = ['token', 'card_type', 'masked_card_number', 'log']
    readonly_fields = fields


@admin.register(models.CyberSourceReply)
class CyberSourceReplyAdmin(admin.ModelAdmin):
    list_filter = ['date_modified', 'date_created']
    list_display = ['date_created', 'user', 'order', 'date_modified']
    fields = ['user', 'order', 'data', 'date_modified', 'date_created']
    readonly_fields = fields
