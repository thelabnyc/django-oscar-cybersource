import datetime

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("cybersource", "0001_initial"),
        ("payment", "0002_auto_20141007_2032"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="transaction",
            options={},
        ),
        migrations.AddField(
            model_name="transaction",
            name="log",
            field=models.ForeignKey(
                related_name="transactions",
                default=0,
                to="cybersource.CyberSourceReply",
                on_delete=models.CASCADE,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="transaction",
            name="processed_datetime",
            field=models.DateTimeField(
                default=datetime.datetime(2016, 4, 4, 12, 49, 59, 226148)
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="transaction",
            name="request_token",
            field=models.CharField(max_length=200, default=""),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="transaction",
            name="token",
            field=models.ForeignKey(
                null=True,
                related_name="transactions",
                on_delete=django.db.models.deletion.SET_NULL,
                blank=True,
                to="cybersource.PaymentToken",
            ),  # NOQA
        ),
    ]
