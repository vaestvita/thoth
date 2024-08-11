from django.contrib import admin
from .models import Waba, Phone
from bitrix.crest import call_method
from bitrix.utils import messageservice_add
from bitrix.models import Line

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
                payload = {'CONFIG_ID': phone.line.line_id}
                call_method(phone.waba.bitrix, 'imopenlines.config.delete', payload)
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        for obj in queryset:
            for phone in obj.phones.all():
                if phone.line:
                    payload = {'CONFIG_ID': phone.line.line_id}
                    call_method(phone.waba.bitrix, 'imopenlines.config.delete', payload)
        super().delete_queryset(request, queryset)


@admin.register(Phone)
class PhoneAdmin(admin.ModelAdmin):
    list_display = ('phone', 'phone_id', 'owner', 'waba', 'line', 'sms_service')
    search_fields = ('phone', 'phone_id')
    fields = ('phone', 'phone_id', 'waba', 'owner', 'line', 'sms_service')
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

            create_line = call_method(obj.waba.bitrix, 'imopenlines.config.add', line_data)

            # активация открытой линии
            if 'result' in create_line:
                line = Line.objects.create(
                    line_id=create_line['result'],
                    portal=obj.waba.bitrix,
                    content_object=obj
                )
                obj.line = line
                obj.save()

                payload = {
                    'CONNECTOR': 'thoth_waba',
                    'LINE': line.line_id,
                    'ACTIVE': 1
                }

                call_method(obj.waba.bitrix, 'imconnector.activate', payload)

        # Регистрация SMS-провайдера
        if obj.sms_service and not obj.old_sms_service:
            api_key = request.user.auth_token.key
            messageservice_add(obj.waba.bitrix, obj.phone, obj.line.line_id, api_key)
        elif not obj.sms_service and obj.old_sms_service:
            call_method(obj.waba.bitrix, 'messageservice.sender.delete', {'CODE': f'THOTH_WABA_{obj.phone}_{obj.line.line_id}'})

        obj.old_sms_service = obj.sms_service
        obj.save()

    # Удаление
    def delete_model(self, request, obj):
        self._delete_related_lines_and_providers(obj)
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        for obj in queryset:
            self._delete_related_lines_and_providers(obj)
        super().delete_queryset(request, queryset)

    def _delete_related_lines_and_providers(self, obj):
        if obj.line:
            call_method(obj.waba.bitrix, 'imopenlines.config.delete', {'CONFIG_ID': obj.line.line_id})
            call_method(obj.waba.bitrix, 'messageservice.sender.delete', {'CODE': f'THOTH_WABA_{obj.phone}_{obj.line.line_id}'})
