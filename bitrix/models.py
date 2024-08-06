from django.db import models
from django.conf import settings

class Bitrix(models.Model):
    domain = models.CharField(max_length=255, unique=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, blank=True)
    storage_id = models.CharField(max_length=255, blank=True)
    client_endpoint = models.CharField(max_length=255)
    access_token = models.CharField(max_length=255)
    refresh_token = models.CharField(max_length=255)
    application_token = models.CharField(max_length=255)
    client_id = models.CharField(max_length=255, blank=True)
    client_secret = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.domain
