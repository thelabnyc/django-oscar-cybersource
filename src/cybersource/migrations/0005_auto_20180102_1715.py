# -*- coding: utf-8 -*-
# Generated by Django 1.11.9 on 2018-01-02 17:15
from __future__ import unicode_literals
from django.db import migrations


def populate_sa_profile(apps, schema_editor):
    SecureAcceptanceProfile = apps.get_model('cybersource', 'SecureAcceptanceProfile')
    from django.conf import settings
    if hasattr(settings, 'CYBERSOURCE_PROFILE') and hasattr(settings, 'CYBERSOURCE_ACCESS') and hasattr(settings, 'CYBERSOURCE_SECRET'):
        profile = SecureAcceptanceProfile()
        profile.hostname = ''
        profile.profile_id = settings.CYBERSOURCE_PROFILE
        profile.access_key = settings.CYBERSOURCE_ACCESS
        profile.secret_key = settings.CYBERSOURCE_SECRET
        profile.is_default = True
        profile.save()


def empty_sa_profile(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('cybersource', '0004_auto_20180102_1714'),
    ]

    operations = [
        migrations.RunPython(populate_sa_profile, empty_sa_profile),
    ]
