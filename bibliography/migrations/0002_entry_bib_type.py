# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2016-11-13 21:32
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bibliography', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='entry',
            name='bib_type',
            field=models.CharField(default=b'', max_length=30),
        ),
    ]