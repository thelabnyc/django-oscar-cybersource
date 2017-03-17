# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.contrib.postgres.fields.hstore
from django.contrib.postgres.operations import HStoreExtension
import django.db.models.deletion
import cybersource.models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        HStoreExtension(),
        migrations.CreateModel(
            name='CyberSourceReply',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, verbose_name='ID', auto_created=True)),
                ('data', django.contrib.postgres.fields.hstore.HStoreField()),
                ('date_modified', models.DateTimeField(auto_now=True, verbose_name='Date Modified')),
                ('date_created', models.DateTimeField(auto_now_add=True, verbose_name='Date Received')),
                ('user', models.ForeignKey(blank=True, to=settings.AUTH_USER_MODEL, related_name='cybersource_replies', on_delete=django.db.models.deletion.SET_NULL, null=True)),  # NOQA
            ],
        ),
        migrations.CreateModel(
            name='PaymentToken',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, verbose_name='ID', auto_created=True)),
                ('token', models.CharField(unique=True, max_length=100)),
                ('masked_card_number', models.CharField(max_length=25)),
                ('card_type', models.CharField(max_length=10)),
                ('log', models.ForeignKey(related_name='tokens', to='cybersource.CyberSourceReply')),
            ],
            bases=(cybersource.models.ReplyLogMixin, models.Model),
        ),
    ]
