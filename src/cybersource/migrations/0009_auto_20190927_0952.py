# Generated by Django 2.2.5 on 2019-09-27 09:52

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('cybersource', '0008_auto_20190515_1550'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='cybersourcereply',
            options={'ordering': ('date_created',), 'verbose_name': 'CyberSource Reply', 'verbose_name_plural': 'CyberSource Replies'},
        ),
        migrations.AlterModelOptions(
            name='paymenttoken',
            options={'verbose_name': 'Payment Token', 'verbose_name_plural': 'Payment Token'},
        ),
        migrations.AlterModelOptions(
            name='secureacceptanceprofile',
            options={'verbose_name': 'Secure Acceptance Profile', 'verbose_name_plural': 'Secure Acceptance Profiles'},
        ),
    ]