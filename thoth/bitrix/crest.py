import logging

import requests
from django.db import transaction
from django.http import JsonResponse

from .models import AppInstance

logger = logging.getLogger("django")


def call_method(appinstance: AppInstance, b24_method: str, data: dict):
    endpoint = appinstance.portal.client_endpoint
    access_token = appinstance.access_token

    try:
        payload = {"auth": access_token, **data}
        logger.debug(f"Data send to b24: {payload}")
        response = requests.post(f"{endpoint}{b24_method}", json=payload)

        if (
            response.status_code == 401
            and response.json().get("error") == "expired_token"
        ):
            refresh_token(appinstance)
            return call_method(appinstance, b24_method, data)

        logger.debug(f"request ended: {response} {response.json()}")
        return response.json()

    except (requests.HTTPError, Exception) as e:
        logger.error(f"General error occurred: {e}")
        return JsonResponse({"detail": str(e)}, status=500)


def refresh_token(appinstance: AppInstance):
    payload = {
        "grant_type": "refresh_token",
        "client_id": appinstance.app.client_id,
        "client_secret": appinstance.app.client_secret,
        "refresh_token": appinstance.refresh_token,
    }
    try:
        response = requests.post("https://oauth.bitrix.info/oauth/token/", data=payload)
        response_data = response.json()

        if response.status_code != 200:
            raise Exception(f"Failed to refresh token: {response_data}")

        appinstance.access_token = response_data["access_token"]
        appinstance.refresh_token = response_data["refresh_token"]

        with transaction.atomic():
            appinstance.save()

        return appinstance
    except Exception as e:
        logger.error(
            f"Error refreshing token: {e}, response_data: {response_data if 'response_data' in locals() else 'No response data'}",
        )
        return JsonResponse({"detail": str(e)}, status=500)
