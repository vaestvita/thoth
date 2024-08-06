import logging
import requests
from django.http import JsonResponse
from django.db import transaction
from .models import Bitrix

logger = logging.getLogger('django')


def call_method(portal_domain: str, http_method: str, b24_method: str, data: dict):
    try:
        # Получение данных портала из базы данных
        portal = Bitrix.objects.get(domain=portal_domain)
    except Bitrix.DoesNotExist:
        return JsonResponse({"detail": "Portal not found"}, status=404)

    endpoint = portal.client_endpoint
    auth_token = portal.access_token

    try:
        payload = {'auth': auth_token, **data}
        if http_method == 'GET':
            url = f"{endpoint}/{b24_method}"
            response = requests.get(url, params=payload)
        elif http_method == 'POST':
            url = f"{endpoint}/{b24_method}"
            response = requests.post(url, json=payload)
        else:
            return JsonResponse({"detail": "Unsupported HTTP method"}, status=400)

        if response.status_code == 401 and response.json().get('error') == 'expired_token':
            refresh_token(portal)
            return call_method(portal_domain, http_method, b24_method, data)

        return response.json()
    
    except requests.HTTPError as http_exc:
        logger.error(f"HTTP error occurred: {http_exc}")
        return JsonResponse({"detail": str(http_exc)}, status=500)
    except Exception as e:
        logger.error(f"General error occurred: {e}")
        return JsonResponse({"detail": str(e)}, status=500)


def refresh_token(portal: Bitrix):
    payload = {
        'grant_type': 'refresh_token',
        'client_id': portal.client_id,
        'client_secret': portal.client_secret,
        'refresh_token': portal.refresh_token,
    }
    try:
        response = requests.post('https://oauth.bitrix.info/oauth/token/', data=payload)
        response_data = response.json()
        portal.access_token = response_data['access_token']
        portal.refresh_token = response_data['refresh_token']

        with transaction.atomic():
            portal.save()

        return portal
    except Exception as e:
        logger.error(f"Error refreshing token: {e}")
        return JsonResponse({"detail": str(e)}, status=500)
