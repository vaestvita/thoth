import logging

import requests
from celery import shared_task

from thoth.bitrix.crest import call_method

from .models import OlxUser
from .utills import refresh_token

logger = logging.getLogger("django")


@shared_task
def get_threads(olx_user_id):
    try:
        user = OlxUser.objects.get(olx_id=olx_user_id)
        # Логируем информацию о пользователе
        logger.info(f"Processing OLX threads for user {user.olx_id}")

        # Получаем домен и токен авторизации из модели OlxUser
        olx_app = user.olxapp
        api_url = f"https://www.{olx_app.client_domain}/api/partner/threads/"
        headers = {
            "Authorization": f"Bearer {user.access_token}",
            "Version": "2.0",
        }

        # Выполняем GET-запрос к API OLX
        response = requests.get(api_url, headers=headers)

        # Проверяем статус ответа
        if response.status_code == 200:
            # Логируем успешный ответ
            threads = response.json().get("data", [])
            logger.debug(f"Received {len(threads)} threads for user {user.olx_id}")

            # Обрабатываем каждый thread, где есть непрочитанные сообщения
            for thread in threads:
                unread_count = thread.get("unread_count", 0)
                if unread_count != 0:
                    thread_id = thread.get("id")
                    advert_id = thread.get("advert_id")
                    interlocutor_id = thread.get("interlocutor_id")
                    messages_url = f"https://www.{olx_app.client_domain}/api/partner/threads/{thread_id}/messages"
                    messages_response = requests.get(messages_url, headers=headers)

                    if messages_response.status_code == 200:
                        messages = messages_response.json().get("data", [])
                        logger.debug(
                            f"Received {len(messages)} messages for thread {thread_id}",
                        )

                        # Отбираем последние непрочитанные сообщения с типом "received"
                        received_messages = [
                            msg for msg in messages if msg["type"] == "received"
                        ]
                        unread_messages = sorted(
                            received_messages,
                            key=lambda x: x["created_at"],
                        )[-unread_count:]

                        # Отправляем выбранные непрочитанные сообщения
                        for msg in unread_messages:
                            logger.debug(
                                f"Unread Received Message in thread {thread_id}: {msg}",
                            )

                            # Формируем массив файлов, если есть прикрепления
                            files = []
                            for attachment in msg.get("attachments", []):
                                files.append({"url": attachment.get("url")})

                            payload = {
                                "CONNECTOR": "thoth_olx",
                                "LINE": user.line.line_id,
                                "MESSAGES": [
                                    {
                                        "user": {
                                            "id": interlocutor_id,
                                        },
                                        "chat": {
                                            "id": f"{thread_id}-{olx_user_id}-{interlocutor_id}",
                                            "url": f"https://www.{olx_app.client_domain}/d/{advert_id}/",
                                        },
                                        "message": {
                                            "text": msg.get("text", "none"),
                                            "files": files,
                                        },
                                    },
                                ],
                            }
                            logger.debug(f"data for b24 message {payload}")
                            call_method(
                                user.line.app_instance,
                                "imconnector.send.messages",
                                payload,
                            )

                        # Помечаем диалог как прочитанный
                        commands_url = f"https://www.{olx_app.client_domain}/api/partner/threads/{thread_id}/commands"
                        requests.post(
                            commands_url,
                            headers=headers,
                            json={"command": "mark-as-read"},
                        )

                    else:
                        logger.error(
                            f"Failed to retrieve messages for thread {thread_id}. "
                            f"Status Code: {messages_response.status_code}, Response: {messages_response.json()}",
                        )

        elif response.status_code == 401:
            refresh_token(olx_user_id)

        else:
            # Логируем ошибки, если ответ не 200
            logger.error(
                f"Failed to retrieve threads for user {user.olx_id}. "
                f"Status Code: {response.status_code}, Response: {response.json()}",
            )

    except OlxUser.DoesNotExist:
        # Логируем ошибку, если пользователь не найден
        logger.error(f"User with ID {olx_user_id} does not exist.")
    except Exception as e:
        # Логируем любые другие ошибки, которые могут возникнуть
        logger.error(
            f"An error occurred while processing OLX threads for user {olx_user_id}: {e!s}",
        )
