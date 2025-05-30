# Generated by Django 1.9.6 on 2016-06-01 19:49

from django.db import migrations, models
from django.utils import timezone
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("payment", "0003_auto_20160404_1250"),
    ]

    operations = [
        migrations.AlterField(
            model_name="transaction",
            name="log",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="transactions",
                to="cybersource.CyberSourceReply",
            ),  # NOQA
        ),
        migrations.AlterField(
            model_name="transaction",
            name="processed_datetime",
            field=models.DateTimeField(default=timezone.now),
        ),
        migrations.AlterField(
            model_name="transaction",
            name="request_token",
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
    ]
