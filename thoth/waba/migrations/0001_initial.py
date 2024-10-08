# Generated by Django 5.0.8 on 2024-08-20 12:39

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('bitrix', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Waba',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, unique=True)),
                ('verify_token', models.CharField(default=uuid.uuid4, editable=False, max_length=100, unique=True)),
                ('access_token', models.CharField(max_length=255)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Phone',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('phone', models.CharField(max_length=20, unique=True)),
                ('phone_id', models.CharField(max_length=50, unique=True)),
                ('sms_service', models.BooleanField(default=False)),
                ('old_sms_service', models.BooleanField(default=False)),
                ('app_instance', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='phones', to='bitrix.appinstance')),
                ('line', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='phones', to='bitrix.line')),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('waba', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='phones', to='waba.waba')),
            ],
        ),
    ]
