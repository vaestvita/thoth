from django.db import models
from django.conf import settings

from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

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


class Line(models.Model):
    line_id = models.CharField(max_length=50)
    portal = models.ForeignKey(Bitrix, on_delete=models.CASCADE, related_name='lines')

    # Обобщенное отношение (Generic Relation)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    def __str__(self):
        return f"Line {self.line_id} on {self.portal}"