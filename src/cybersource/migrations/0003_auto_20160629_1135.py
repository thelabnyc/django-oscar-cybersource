# Generated by Django 1.9.6 on 2016-06-29 11:35

from django.db import migrations


def assign_orders(apps, schema_editor):
    # We can't import the Person model directly as it may be a newer
    # version than this migration expects. We use the historical version.
    CyberSourceReply = apps.get_model("cybersource", "CyberSourceReply")
    Order = apps.get_model("order", "Order")
    for reply in CyberSourceReply.objects.filter(order=None).all():
        try:
            order = Order.objects.get(number=reply.data.get("req_reference_number"))
            reply.order = order
            reply.save()
        except Order.DoesNotExist:
            pass


class Migration(migrations.Migration):
    dependencies = [
        ("cybersource", "0002_cybersourcereply_order"),
    ]

    operations = [
        migrations.RunPython(assign_orders),
    ]
