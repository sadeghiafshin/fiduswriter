# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelTable('UserProfile', 'user_userprofile'),
        migrations.AlterModelTable('TeamMember', 'user_teammember')
    ]
