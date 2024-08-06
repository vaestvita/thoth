from django.contrib import admin
from .models import Bitrix

@admin.register(Bitrix)
class BitrixAdmin(admin.ModelAdmin):
    list_display = ('domain', 'owner', 'storage_id')
    search_fields = ('domain',)
    list_filter = ('domain',)
    readonly_fields = ('domain', 'storage_id', 'client_endpoint', 'access_token', 'refresh_token', 'application_token')
    fields = ('domain', 'owner', 'storage_id', 'client_endpoint', 'access_token', 'refresh_token', 'application_token', 'client_id', 'client_secret')
