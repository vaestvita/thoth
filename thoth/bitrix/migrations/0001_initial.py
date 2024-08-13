# Generated by Django 5.0.7 on 2024-08-10 14:21

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Bitrix',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('domain', models.CharField(max_length=255, unique=True)),
                ('storage_id', models.CharField(blank=True, max_length=255)),
                ('client_endpoint', models.CharField(max_length=255)),
                ('access_token', models.CharField(max_length=255)),
                ('refresh_token', models.CharField(max_length=255)),
                ('application_token', models.CharField(max_length=255)),
                ('client_id', models.CharField(blank=True, max_length=255)),
                ('client_secret', models.CharField(blank=True, max_length=255)),
                ('owner', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Line',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('line_id', models.CharField(max_length=50)),
                ('object_id', models.PositiveIntegerField()),
                ('content_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='contenttypes.contenttype')),
                ('portal', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='lines', to='bitrix.bitrix')),
            ],
        ),
    ]