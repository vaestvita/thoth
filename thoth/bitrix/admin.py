from django import forms
from django.contrib import admin

from .models import App, AppInstance, Bitrix, Line


@admin.register(App)
class AppAdmin(admin.ModelAdmin):
    list_display = ("name", "id", "site")
    search_fields = ("name",)
    fields = ("owner", "connector", "site", "name", "client_id", "client_secret")


@admin.register(AppInstance)
class AppInstanceAdmin(admin.ModelAdmin):
    list_display = ("id", "owner", "app", "portal")
    fields = (
        "id",
        "owner",
        "app",
        "portal",
        "auth_status",
        "storage_id",
        "access_token",
        "refresh_token",
        "application_token",
    )
    readonly_fields = (
        "id",
        "app",
        "portal",
        "auth_status",
        "storage_id",
        "access_token",
        "refresh_token",
        "application_token",
    )


@admin.register(Bitrix)
class BitrixAdmin(admin.ModelAdmin):
    list_display = ("domain", "owner")
    search_fields = ("domain",)
    readonly_fields = ("domain", "client_endpoint", "user_id")
    fields = ("domain", "client_endpoint", "owner", "user_id")


@admin.register(Line)
class LineAdmin(admin.ModelAdmin):
    list_display = ("line_id", "app_instance")
    search_fields = ("line_id",)
    fields = ("line_id", "app_instance")
    readonly_fields = ("line_id", "app_instance")