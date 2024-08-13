import logging

import requests
from django.db import transaction
from django.http import JsonResponse
from django.conf import settings

from .models import Bitrix

logger = logging.getLogger("django")

BITRIX_CLIENT_ID = settings.BITRIX_CLIENT_ID
BITRIX_CLIENT_SECRET = settings.BITRIX_CLIENT_SECRET

def call_method(portal_domain: str, b24_method: str, data: dict):
    try:
        # Получение данных портала из базы данных
        portal = Bitrix.objects.get(domain=portal_domain)
    except Bitrix.DoesNotExist:
        logger.error(f"Portal not found: {portal_domain}")
        return JsonResponse({"detail": "Portal not found"}, status=404)

    endpoint = portal.client_endpoint
    access_token = portal.access_token

    try:
        payload = {"auth": access_token, **data}
        logger.debug(f"Data send to b24: {payload}")
        response = requests.post(f"{endpoint}{b24_method}", json=payload)

        if (
            response.status_code == 401
            and response.json().get("error") == "expired_token"
        ):
            refresh_token(portal)
            return call_method(portal_domain, b24_method, data)

        logger.debug(f"request ended: {response} {response.json()}")
        return response.json()

    except (requests.HTTPError, Exception) as e:
        logger.error(f"General error occurred: {e}")
        return JsonResponse({"detail": str(e)}, status=500)



def refresh_token(portal: Bitrix):
    client_id = portal.client_id or BITRIX_CLIENT_ID
    client_secret = portal.client_secret or BITRIX_CLIENT_SECRET

    payload = {
        "grant_type": "refresh_token",
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": portal.refresh_token,
    }
    try:
        response = requests.post("https://oauth.bitrix.info/oauth/token/", data=payload)
        response_data = response.json()

        if response.status_code != 200:
            raise Exception(f"Failed to refresh token: {response_data}")

        portal.access_token = response_data["access_token"]
        portal.refresh_token = response_data["refresh_token"]

        with transaction.atomic():
            portal.save()

        return portal
    except Exception as e:
        logger.error(
            f"Error refreshing token: {e}, response_data: {response_data if 'response_data' in locals() else 'No response data'}",
        )
        return JsonResponse({"detail": str(e)}, status=500)
