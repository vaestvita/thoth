from django.contrib import admin
from .models import Waba, Phone
from bitrix.crest import call_method

@admin.register(Waba)
class WabaAdmin(admin.ModelAdmin):
    list_display = ('name', 'verify_token', 'owner', 'bitrix')
    search_fields = ('name', 'bitrix')
    fields = ('name', 'verify_token', 'access_token', 'owner', 'bitrix')
    readonly_fields = ('verify_token',)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

    # Удаление всех линий, связанных с Waba
    def delete_model(self, request, obj):
        for phone in obj.phones.all():
            if phone.line:
                payload = {'CONFIG_ID': phone.line}
                call_method(phone.waba.bitrix, 'POST', 'imopenlines.config.delete', payload)
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        for obj in queryset:
            for phone in obj.phones.all():
                if phone.line:
                    payload = {'CONFIG_ID': phone.line}
                    call_method(phone.waba.bitrix, 'POST', 'imopenlines.config.delete', payload)
        super().delete_queryset(request, queryset)


@admin.register(Phone)
class PhoneAdmin(admin.ModelAdmin):
    list_display = ('phone', 'phone_id', 'owner', 'waba', 'line')
    search_fields = ('phone', 'phone_id')
    fields = ('phone', 'phone_id', 'waba', 'owner', 'line')
    readonly_fields = ('line',)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        # создание открытой линии
        if not obj.line:
            line_data = {
                'PARAMS': {
                    'LINE_NAME': f'THOTH_{obj.phone}'
                }
            }

            create_line = call_method(obj.waba.bitrix, 'POST', 'imopenlines.config.add', line_data)

            # активация открытой линии
            if 'result' in create_line:
                obj.line = create_line['result']
                obj.save()

                payload = {
                    'CONNECTOR': 'thoth_waba',
                    'LINE': obj.line,
                    'ACTIVE': 1
                }

                call_method(obj.waba.bitrix, 'POST', 'imconnector.activate', payload)

    # Удаление открытой линии
    def delete_model(self, request, obj):
        if obj.line:
            payload = {'CONFIG_ID': obj.line}
            call_method(obj.waba.bitrix, 'POST', 'imopenlines.config.delete', payload)
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        for obj in queryset:
            if obj.line:
                payload = {'CONFIG_ID': obj.line}
                call_method(obj.waba.bitrix, 'POST', 'imopenlines.config.delete', payload)
        super().delete_queryset(request, queryset)
