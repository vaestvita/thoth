import base64
import json
import logging
import os
import re

from django.conf import settings
from rest_framework import status
from rest_framework.response import Response

import thoth.olx.utills
import thoth.waba.utils
from thoth.olx.models import OlxUser
from thoth.waba.models import Phone

from .crest import call_method
from .models import Bitrix
from .models import Line

logger = logging.getLogger("django")

HOME_URL = settings.HOME_URL
EVENTS = [
    "ONIMCONNECTORMESSAGEADD",
    "ONIMCONNECTORLINEDELETE",
    "ONIMCONNECTORSTATUSDELETE",
]
CONNECTORS = ["waba", "olx"]


def thoth_logo(connetor):
    dir = os.path.dirname(os.path.abspath(__file__))
    image = os.path.join(dir, "img", f"{connetor}.svg")

    with open(image, "rb") as file:
        image_data = file.read()
        encoded_image = base64.b64encode(image_data).decode("utf-8")
        return f"data:image/svg+xml;base64,{encoded_image}"


# Регистрация коннектора
def register_connector(domain, api_key):
    for connetor in CONNECTORS:
        payload = {
            "ID": f"thoth_{connetor}",
            "NAME": f"THOTH {connetor.upper()}",
            "ICON": {
                "DATA_IMAGE": thoth_logo(connetor),
            },
            "PLACEMENT_HANDLER": f"{HOME_URL}/api/bitrix/placement/?api-key={api_key}",
        }

        call_method(domain, "imconnector.register", payload)

    # Подписка на события
    for event in EVENTS:
        payload = {
            "event": event,
            "HANDLER": f"{HOME_URL}/api/bitrix/?api-key={api_key}",
        }

        call_method(domain, "event.bind", payload)


# Регистрация SMS-провайдера
def messageservice_add(domain, phone, line, api_key):
    payload = {
        "CODE": f"THOTH_WABA_{phone}_{line}",
        "NAME": f"THOTH WABA ({phone})",
        "TYPE": "SMS",
        "HANDLER": f"{HOME_URL}/api/bitrix/sms/?api-key={api_key}",
    }

    return call_method(domain, "messageservice.sender.add", payload)


def get_personal_mobile(users):
    personal_mobiles = []
    for user_id, user_info in users.items():
        if user_info.get("external_auth_id") == "imconnector":
            phones = user_info.get("phones", {})
            personal_mobile = phones.get("personal_mobile")
            if personal_mobile:
                personal_mobiles.append(personal_mobile)
    return personal_mobiles


def extract_files(data):
    files = []
    i = 0
    while True:
        # Формируем ключи для доступа к данным файлов
        name_key = f"data[MESSAGES][0][message][files][{i}][name]"
        link_key = f"data[MESSAGES][0][message][files][{i}][link]"
        type_key = f"data[MESSAGES][0][message][files][{i}][type]"

        # Проверяем, существуют ли такие ключи в словаре
        if name_key in data and link_key in data:
            # Добавляем название и ссылку в список
            files.append(
                {
                    "name": data.get(name_key),
                    "link": data.get(link_key),
                    "type": data.get(type_key),
                },
            )
            i += 1
        else:
            break

    return files


def process_placement(request):
    try:
        data = request.data
        placement_options = data.get("PLACEMENT_OPTIONS", {})
        domain = request.query_params.get("DOMAIN", {})

        if not placement_options:
            return Response(
                {"error": "PLACEMENT_OPTIONS is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        placement_options = json.loads(placement_options)
        line_id = placement_options.get("LINE")
        connector = placement_options.get("CONNECTOR")

        line_data = call_method(
            domain,
            "imopenlines.config.get",
            {"CONFIG_ID": line_id},
        )
        if "result" in line_data:
            portal = Bitrix.objects.filter(domain=domain).first()

            if not portal:
                return Response(
                    {"error": "Domain not found"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            element_id = None
            content_object = None

            if connector == "thoth_waba":
                try:
                    _, element_id = line_data["result"]["LINE_NAME"].split("_")
                except ValueError as e:
                    logger.error(f"Error parsing LINE_NAME: {e}")
                    return Response(
                        {
                            "error": "Invalid LINE_NAME format. Correct is THOTH_XXXXXXXXX",
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                phone = Phone.objects.filter(phone=element_id).first()
                if phone:
                    content_object = phone
                else:
                    return Response(
                        {"error": f"Phone {element_id} not found in THOTH base"},
                        status=status.HTTP_404_NOT_FOUND,
                    )

            elif connector == "thoth_olx":
                try:
                    _, _, element_id = line_data["result"]["LINE_NAME"].split("_")
                except ValueError as e:
                    logger.error(f"Error parsing LINE_NAME: {e}")
                    return Response(
                        {
                            "error": "Invalid LINE_NAME format. Correct is THOTH_OLX_XXXXX",
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                olxuser = OlxUser.objects.filter(olx_id=element_id).first()
                if olxuser:
                    content_object = olxuser
                else:
                    return Response(
                        {
                            "error": f"OLX user with the ID {element_id} not found in THOTH base",
                        },
                        status=status.HTTP_404_NOT_FOUND,
                    )

            # Создаем или получаем линию и связываем с найденным объектом
            line, created = Line.objects.get_or_create(
                line_id=line_id,
                portal=portal,
                defaults={"content_object": content_object},
            )

            if not created:
                line.content_object = content_object
                line.save()

            if isinstance(content_object, Phone) or isinstance(content_object, OlxUser):
                content_object.line = line
            content_object.save()

            payload = {
                "CONNECTOR": connector,
                "LINE": line_id,
                "ACTIVE": 1,
            }

            resp = call_method(domain, "imconnector.activate", payload)

            return Response(resp, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return Response(
            {"error": "An unexpected error occurred"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


def sms_processor(request):
    data = request.data
    domain = data.get("auth[domain]", {})
    sms_msg = data.get("type", {})
    message_body = data.get("message_body", {})

        # Messages from SMS gate
    if sms_msg == "SMS":
        phones = []
        message_to = data.get("message_to", {})
        phones.append(message_to)

        try:
            template, language = message_body.split("+")
        except ValueError as e:
            logger.error(f"Error splitting message_body: {message_body} - {str(e)}")
            return Response({"error": "Invalid message body content"}, status=status.HTTP_400_BAD_REQUEST)
        message = {
            "type": "template",
            "template": {"name": template, "language": {"code": language}},
        }
        code = data.get("code", {})
        line = re.search(r"_(\d+)$", code).group(1)

        thoth.waba.utils.send_message(domain, message, line, phones)
        return Response({"status": "message processed"}, status=status.HTTP_200_OK)



def event_processor(self, request):
    try:
        data = request.data
        event = data.get("event", {})
        domain = data.get("auth[domain]", {})
        auth_status = data.get("auth[status]", {})
        client_endpoint = data.get("auth[client_endpoint]", {})
        access_token = data.get("auth[access_token]", {})
        refresh_token = data.get("auth[refresh_token]", {})
        application_token = data.get("auth[application_token]", {})
        api_key = request.query_params.get("api-key", {})
        
        # Проверка наличия домена в базе данных
        try:
            portal = Bitrix.objects.get(domain=domain)
            # Обновление access_token
            portal.access_token = access_token
            portal.save()

        except Bitrix.DoesNotExist:
            # Если событие ONAPPINSTALL, сохраняем данные домена в базу
            if event == "ONAPPINSTALL":
                bitrix_data = {
                    "domain": domain,
                    "client_endpoint": client_endpoint,
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "application_token": application_token,
                }

                """
                Если приложение локальное, то привязываем к пользователю
                Если тиражное (F), то портал привязывается вручную
                """
                if auth_status == 'L':
                    bitrix_data["owner"] = request.user.id

                # Create the portal with the domain and access token
                serializer = self.get_serializer(data=bitrix_data)
                if not serializer.is_valid():
                    logger.error("Serializer Errors: ", serializer.errors)
                    return Response(
                        serializer.errors,
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                self.perform_create(serializer)

                storage_id_data = call_method(domain, "disk.storage.getforapp", {})
                storage_id = storage_id_data["result"]["ID"]

                portal = Bitrix.objects.get(domain=domain)
                portal.storage_id = storage_id
                portal.save()

                # imconnector register
                register_connector(domain, api_key)

                headers = self.get_success_headers(serializer.data)
                return Response(
                    serializer.data,
                    status=status.HTTP_201_CREATED,
                    headers=headers,
                )
            else:
                return Response(
                    {"error": "Domain not found and not an install event"},
                    status=status.HTTP_400_BAD_REQUEST,
                )


        # Обработка события ONIMCONNECTORMESSAGEADD
        if event == "ONIMCONNECTORMESSAGEADD":
            connector = data.get("data[CONNECTOR]")
            line = data.get("data[LINE]", {})
            message_id = data.get("data[MESSAGES][0][im][message_id]")
            file_type = data.get("data[MESSAGES][0][message][files][0][type]", None)
            text = data.get("data[MESSAGES][0][message][text]", None)
            if text:
                text = re.sub(r"\[(?!(br|\n))[^\]]+\]", "", text)
                text = text.replace("[br]", "\n")

            files = []
            if file_type:
                files = extract_files(data)

            # If WABA connector
            if connector == "thoth_waba":
                chat_id = data.get("data[MESSAGES][0][im][chat_id]")
                message = {
                    "biz_opaque_callback_data": f"{line}_{chat_id}_{message_id}",
                }

                if not files and text:
                    message["type"] = "text"
                    message["text"] = {"body": text}

                # Обработка шаблонных сообщений
                if "template-" in text:
                    _, template_body = text.split("-")
                    template, language = template_body.split("+")
                    message["type"] = "template"
                    message["template"] = {
                        "name": template,
                        "language": {"code": language},
                    }

                # Получаем список пользователей и номера телефонов
                user_list = call_method(
                    domain,
                    "im.chat.user.list",
                    {"CHAT_ID": chat_id},
                )
                if user_list:
                    users = call_method(
                        domain,
                        "im.user.list.get",
                        {"ID": user_list["result"]},
                    )
                    phones = get_personal_mobile(users["result"])

                    # Если есть файлы, отправляем сообщение с каждым файлом отдельно
                    if files:
                        for file in files:
                            file_message = message.copy()

                            # Определяем тип файла и добавляем его к сообщению
                            if file["type"] == "image":
                                file_message["type"] = "image"
                                file_message["image"] = {"link": file["link"]}
                            elif file["type"] in ["file", "video", "audio"]:
                                file_message["type"] = "document"
                                file_message["document"] = {
                                    "link": file["link"],
                                    "filename": file["name"],
                                }

                            thoth.waba.utils.send_message(
                                domain,
                                file_message,
                                line,
                                phones,
                            )
                    else:
                        # Если файлов нет, отправляем только текстовое сообщение
                        thoth.waba.utils.send_message(domain, message, line, phones)

            # If OLX connector
            elif connector == "thoth_olx":
                chat_id = data.get("data[MESSAGES][0][chat][id]")
                resp = thoth.olx.utills.send_message(chat_id, text, files)
                if resp.status_code == 200:
                    payload = {
                        "CONNECTOR": "thoth_olx",
                        "LINE": line,
                        "MESSAGES": [
                            {
                                "im": {
                                    "chat_id": chat_id,
                                    "message_id": message_id,
                                },
                            },
                        ],
                    }

                    call_method(domain, "imconnector.send.status.delivery", payload)

                else:
                    error_text = resp.json()["error"]["detail"]
                    _, _, interlocutor_id = chat_id.split("-")

                    payload = {
                        "CONNECTOR": "thoth_olx",
                        "LINE": line,
                        "MESSAGES": [
                            {
                                "user": {
                                    "id": interlocutor_id,
                                },
                                "chat": {
                                    "id": chat_id,
                                },
                                "message": {
                                    "text": f"This is a response from the OLX server: {error_text}",
                                },
                            },
                        ],
                    }

                    call_method(domain, "imconnector.send.messages", payload)

            return Response(
                {"status": "ONIMCONNECTORMESSAGEADD event processed"},
                status=status.HTTP_200_OK,
            )

        elif event == "ONIMCONNECTORSTATUSDELETE":
            line_id = data.get("data[line]")
            line = Line.objects.filter(line_id=line_id, portal__domain=domain).first()
            if line:
                content_object = line.content_object
                if isinstance(content_object, Phone) or isinstance(
                    content_object,
                    OlxUser,
                ):
                    content_object.line = None
                    content_object.save()
                line.delete()
                return Response({"status": "Line cleared"}, status=status.HTTP_200_OK)
            else:
                return Response(
                    {"error": "Line not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

        elif event == "ONIMCONNECTORLINEDELETE":
            line = data.get("data")
            return Response({"status": "Line cleared"}, status=status.HTTP_200_OK)

        else:
            return Response(
                {"error": "Unsupported event"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    except Exception as e:
        logger.error(f"Error occurred: {e!s}")
        return Response(
            {"error": "Internal server error"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
