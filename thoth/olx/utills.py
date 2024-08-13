import logging

import requests

from .models import OlxUser

logger = logging.getLogger("django")


def refresh_token(olx_user_id):
    user = OlxUser.objects.get(olx_id=olx_user_id)
    olx_app = user.olxapp
    api_url = f"https://www.{olx_app.client_domain}/api/open/oauth/token"

    payload = {
        "grant_type": "refresh_token",
        "client_id": olx_app.client_id,
        "client_secret": olx_app.client_secret,
        "refresh_token": user.refresh_token,
    }

    get_token = requests.post(api_url, json=payload)

    if get_token.status_code == 200:
        token_data = get_token.json()
        logger.info(f"NEW TOKEN {token_data}")

        # Сохраняем новые токены в базу данных
        user.access_token = token_data.get("access_token")
        user.refresh_token = token_data.get("refresh_token")
        user.save()
        logger.info(f"Tokens updated successfully for user {user.olx_id}")
    else:
        logger.error(
            f"Failed to refresh token for user {user.olx_id}. Status code: {get_token.status_code}, Response: {get_token.text}",
        )


def send_message(chat_id, text, files=None):
    def _send_request(user, api_url, headers, payload):
        response = requests.post(api_url, headers=headers, json=payload)
        return response

    threadid, olx_user_id, _ = chat_id.split("-")
    user = OlxUser.objects.get(olx_id=olx_user_id)
    olx_app = user.olxapp
    api_url = (
        f"https://www.{olx_app.client_domain}/api/partner/threads/{threadid}/messages"
    )

    headers = {
        "Authorization": f"Bearer {user.access_token}",
        "Version": "2.0",
    }

    payload = {
        "text": text,
    }

    # Добавляем attachments
    if files:
        payload["text"] = "files"
        payload["attachments"] = [{"url": file["link"]} for file in files]

    response = _send_request(user, api_url, headers, payload)

    # Если получили 401, обновляем токен и повторяем запрос
    if response.status_code == 401:
        if refresh_token(olx_user_id):
            # Обновляем заголовки с новым токеном
            headers["Authorization"] = f"Bearer {user.access_token}"
            response = _send_request(user, api_url, headers, payload)
        else:
            logger.error(
                f"Failed to refresh token for user {olx_user_id} after receiving 401.",
            )

    return response
