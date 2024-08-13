from django.contrib import admin

from .models import Bitrix
from .models import Line


@admin.register(Bitrix)
class BitrixAdmin(admin.ModelAdmin):
    list_display = ("domain", "owner", "storage_id")
    search_fields = ("domain",)
    list_filter = ("domain",)
    readonly_fields = (
        "domain",
        "storage_id",
        "client_endpoint",
        "access_token",
        "refresh_token",
        "application_token",
    )
    fields = (
        "domain",
        "owner",
        "storage_id",
        "client_endpoint",
        "access_token",
        "refresh_token",
        "application_token",
        "client_id",
        "client_secret",
    )


@admin.register(Line)
class LineAdmin(admin.ModelAdmin):
    list_display = ("line_id", "portal", "content_type", "object_id")
    search_fields = ("line_id", "portal__domain")
