from django.contrib import admin
from django.contrib import messages

from thoth.bitrix.crest import call_method
from thoth.bitrix.models import Line
from thoth.bitrix.utils import messageservice_add

from .models import Phone
from .models import Waba


@admin.register(Waba)
class WabaAdmin(admin.ModelAdmin):
    list_display = ("name", "verify_token", "owner")
    fields = ("name", "access_token", "owner")


@admin.register(Phone)
class PhoneAdmin(admin.ModelAdmin):
    list_display = ("phone", "phone_id", "owner", "waba", "line", "sms_service")
    search_fields = ("phone", "phone_id")
    fields = (
        "app_instance",
        "phone",
        "phone_id",
        "waba",
        "owner",
        "line",
        "sms_service",
    )
    readonly_fields = (
        "line",
    )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        # создание открытой линии
        if not obj.line:
            line_data = {
                "PARAMS": {
                    "LINE_NAME": obj.phone,
                },
            }

            create_line = call_method(
                obj.app_instance, "imopenlines.config.add", line_data
            )

            # активация открытой линии
            if "result" in create_line:
                line = Line.objects.create(
                    line_id=create_line["result"],
                    app_instance=obj.app_instance,
                )
                obj.line = line
                obj.save()

                payload = {
                    "CONNECTOR": "thoth_waba",
                    "LINE": line.line_id,
                    "ACTIVE": 1,
                }

                call_method(obj.app_instance, "imconnector.activate", payload)


        # Регистрация SMS-провайдера
        if obj.sms_service and not obj.old_sms_service:
            # Проверка наличия объекта auth_token
            owner = obj.line.app_instance.app.owner
            if not hasattr(owner, 'auth_token'):
                obj.sms_service = False
                obj.save()
                messages.error(request, f"API key not found for user {owner}. Operation aborted.")
                return

            api_key = owner.auth_token.key
            resp = messageservice_add(obj.app_instance, obj.phone, obj.line.line_id, api_key, 'waba')
            if 'error' in resp:
                obj.sms_service = False
                obj.save()
                messages.error(request, resp)

        elif not obj.sms_service and obj.old_sms_service:
            phone = ''.join(filter(str.isalnum, obj.phone))
            resp = call_method(
                obj.app_instance,
                "messageservice.sender.delete",
                {"CODE": f"THOTH_{phone}_{obj.line.line_id}"},
            )
            if 'error' in resp:
                messages.error(request, resp)

        obj.old_sms_service = obj.sms_service
        obj.save()
