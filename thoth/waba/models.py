import uuid

from django.conf import settings
from django.db import models

from thoth.bitrix.models import AppInstance
from thoth.bitrix.models import Line


class Waba(models.Model):
    name = models.CharField(max_length=255, editable=True, unique=True)
    verify_token = models.CharField(
        max_length=100,
        default=uuid.uuid4,
        editable=False,
        unique=True,
    )
    access_token = models.CharField(max_length=255)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.name}"


class Phone(models.Model):
    phone = models.CharField(max_length=20, unique=True)
    phone_id = models.CharField(max_length=50, unique=True)
    sms_service = models.BooleanField(default=False)
    old_sms_service = models.BooleanField(default=False)
    waba = models.ForeignKey(Waba, on_delete=models.CASCADE, related_name="phones")
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    app_instance = models.ForeignKey(
        AppInstance, on_delete=models.SET_NULL, related_name="phones", null=True
    )
    line = models.ForeignKey(
        Line,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="phones",
    )

    def __str__(self):
        return f"{self.phone} ({self.phone_id})"
