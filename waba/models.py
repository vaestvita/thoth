from django.db import models
from django.conf import settings
import uuid

class Waba(models.Model):
    name = models.CharField(max_length=255, editable=True, unique=True)
    verify_token = models.CharField(max_length=100, default=uuid.uuid4, editable=False, unique=True)
    access_token = models.CharField(max_length=255)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    bitrix = models.ForeignKey('bitrix.Bitrix', on_delete=models.CASCADE, related_name='wabas')

    def __str__(self):
        return f"{self.name} ({self.bitrix})"

class Phone(models.Model):
    phone = models.CharField(max_length=20, unique=True)
    phone_id = models.CharField(max_length=50, unique=True)
    waba = models.ForeignKey(Waba, on_delete=models.CASCADE, related_name='phones')
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    line = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return f"{self.phone} ({self.phone_id})"
