# Generated by Django 2.2.5 on 2019-09-27 09:52

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("payment", "0005_auto_20180102_1714"),
    ]

    operations = [
        migrations.AlterField(
            model_name="transaction",
            name="date_created",
            field=models.DateTimeField(
                auto_now_add=True, db_index=True, verbose_name="Date Created"
            ),
        ),
    ]
