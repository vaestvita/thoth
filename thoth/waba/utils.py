import base64
import logging

import requests
from rest_framework import status
from rest_framework.response import Response

from thoth.bitrix.crest import call_method
from thoth.bitrix.models import Line

from .models import Phone
from .models import Waba

FB_URL = "https://graph.facebook.com/v19.0/"
logger = logging.getLogger("django")


def send_whatsapp_message(access_token, phone_number_id, to, message):
    url = f"{FB_URL}{phone_number_id}/messages"
    headers = {"Authorization": f"Bearer {access_token}"}
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        **message,
    }
    response = requests.post(url, json=payload, headers=headers)
    return response


def send_message(appinstance, message, line_id, phones):
    # Найти объект Line по line_id и домену
    line = Line.objects.filter(line_id=line_id, app_instance=appinstance).first()

    if not line:
        logger.error(f"Line ID {line_id} not found")
        return Response(
            {f"Line ID {line_id} not found"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Найти объект Waba, связанный с этим Line
    waba = Waba.objects.filter(phones__line=line).first()
    if not waba:
        return None

    access_token = waba.access_token
    # Найти номер телефона, связанный с Line
    phone_number = waba.phones.filter(line=line).first()
    phone_number_id = phone_number.phone_id if phone_number else None

    if not phone_number_id:
        return None

    # Отправка сообщения на каждый телефон
    for phone in phones:
        response = send_whatsapp_message(access_token, phone_number_id, phone, message)
        if response.status_code != 200:
            logger.error(f"Failed to send message to {phone}: {response.json()}")
            return Response(
                {f"Failed to send message to {phone}: {response.json()}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        else:
            logger.debug(f"Message sent to {phone}. Result: {response.json()}")
            return Response({f"Message sent to {phone}"}, status=status.HTTP_200_OK)


def get_file(access_token, media_id, filename, appinstance, storage_id):
    headers = {"Authorization": f"Bearer {access_token}"}

    file_data = requests.get(f"{FB_URL}{media_id}", headers=headers)
    if file_data.status_code != 200:
        return None
    file_url = file_data.json().get("url", None)
    download_file = requests.get(file_url, headers=headers)
    if download_file.status_code != 200:
        return None
    fileContent = base64.b64encode(download_file.content).decode("utf-8")

    payload = {
        "id": storage_id,
        "fileContent": fileContent,
        "data": {"NAME": f"{media_id}_{filename}"},
    }

    upload_to_bitrix = call_method(appinstance, "disk.storage.uploadfile", payload)
    if "result" in upload_to_bitrix:
        return upload_to_bitrix["result"]["DOWNLOAD_URL"]
    else:
        return None


def format_contacts(contacts):
    contact_text = "Присланы контакты:\n"
    for i, contact in enumerate(contacts, start=1):
        name = contact["name"]["formatted_name"]
        phones = ", ".join([phone["phone"] for phone in contact.get("phones", [])])
        emails = ", ".join([email["email"] for email in contact.get("emails", [])])

        contact_info = f"{i}. {name}"
        if phones:
            contact_info += f", {phones}"
        if emails:
            contact_info += f", {emails}"

        contact_text += contact_info + "\n"

    return contact_text


def message_processing(request):
    data = request.data
    logger.debug(f"request from waba: {data}")
    message_data = {
        "CONNECTOR": "thoth_waba",
        "MESSAGES": [{"user": {}, "chat": {}, "message": {}}],
    }
    message_data["MESSAGES"][0]["user"]["skip_phone_validate"] = "Y"

    entry = data["entry"][0]
    changes = entry["changes"][0]
    value = changes["value"]
    message_data["MESSAGES"][0]["chat"]["id"] = value["metadata"][
        "display_phone_number"
    ]
    phone_number_id = value["metadata"]["phone_number_id"]

    try:
        phone = Phone.objects.get(phone_id=phone_number_id)
        message_data["LINE"] = phone.line.line_id
        waba = phone.waba
        appinstance = phone.app_instance

        access_token = waba.access_token
        storage_id = phone.app_instance.storage_id
    except Phone.DoesNotExist:
        return Response(
            {"error": "Phone with given phone_number_id not found"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    messages = value.get("messages", [])
    for message in messages:
        message_type = message.get("type")
        message_data["MESSAGES"][0]["user"]["id"] = message["from"]
        message_data["MESSAGES"][0]["user"]["phone"] = message["from"]
        contacts = value.get("contacts", [])
        name = None
        if contacts:
            name = contacts[0].get("profile", {}).get("name")
            message_data["MESSAGES"][0]["user"]["last_name"] = name

        if message_type == "text":
            message_data["MESSAGES"][0]["message"]["text"] = message["text"]["body"]

        elif message_type in ["image", "video", "audio", "document"]:
            media_data = value["messages"][0][message_type]
            media_id = media_data["id"]
            extension = media_data["mime_type"].split("/")[1].split(";")[0]
            filename = media_data.get("filename", f"{media_id}.{extension}")
            message_data["MESSAGES"][0]["message"]["text"] = media_data.get(
                "caption",
                f"{filename}",
            )

            file_url = get_file(
                access_token, media_id, filename, appinstance, storage_id
            )
            if file_url:
                message_data["MESSAGES"][0]["message"]["files"] = [{}]
                message_data["MESSAGES"][0]["message"]["files"][0]["url"] = file_url

        elif message_type == "contacts":
            contacts = value["messages"][0]["contacts"]
            message_data["MESSAGES"][0]["message"]["text"] = format_contacts(contacts)

        call_method(appinstance, "imconnector.send.messages", message_data)

    statuses = value.get("statuses", [])
    for item in statuses:
        status_name = item.get("status")
        callback_data = item.get("biz_opaque_callback_data", None)
        if callback_data:
            line, chat_id, message_id = callback_data.split("_")

            message_data["MESSAGES"][0]["im"] = {
                "chat_id": chat_id,
                "message_id": message_id,
            }

            if status_name == "delivered":
                call_method(
                    appinstance, "imconnector.send.status.delivery", message_data
                )
            elif status_name == "read":
                call_method(
                    appinstance, "imconnector.send.status.reading", message_data
                )

        if status_name == "failed":
            errors = item.get("errors", [])
            logger.error(f"FaceBook Error: {errors}")
            error_messages = []
            for error in errors:
                error_message = f"FaceBook Error Code: {error['code']}, Title: {error['title']}, Message: {error['error_data']['details']}"
                error_messages.append(error_message)
            combined_error_message = " | ".join(error_messages)
            message_data["MESSAGES"][0]["user"]["id"] = item.get("recipient_id")
            message_data["MESSAGES"][0]["message"]["text"] = combined_error_message

            call_method(appinstance, "imconnector.send.messages", message_data)

    return Response({"status": "received"}, status=status.HTTP_200_OK)
