# waba/urls.py
from django.urls import path

from .api.views import WabaWebhook

urlpatterns = [
    path("", WabaWebhook.as_view(), name="waba_webhook"),
]
