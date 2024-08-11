from rest_framework.views import APIView
from rest_framework import status
from django.shortcuts import get_object_or_404
import requests
import logging

from django.shortcuts import render

from olx.models import OlxApp, OlxUser


logger = logging.getLogger('olx')

class OlxAuthorizationAPIView(APIView):
    permission_classes = []

    def get(self, request, *args, **kwargs):
        code = request.query_params.get('code')
        state = request.query_params.get('state')

        account = get_object_or_404(OlxApp, id=state)

        if not account:
            context = {"error": "Account not found"}
            return render(request, 'error.html', context, status=status.HTTP_400_BAD_REQUEST)

        token_url = f"https://www.{account.client_domain}/api/open/oauth/token"
        payload = {
            'grant_type': 'authorization_code',
            'scope': 'v2 read write',
            'code': code,
            'client_id': account.client_id,
            'client_secret': account.client_secret,
        }

        response = requests.post(token_url, json=payload)
        if response.status_code == 200:
            tokens = response.json()
            access_token = tokens.get('access_token')
            refresh_token = tokens.get('refresh_token')

            # Запрос данных пользователя
            user_info_url = f"https://www.{account.client_domain}/api/partner/users/me"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Version": "2.0"
            }

            user_info_response = requests.get(user_info_url, headers=headers)
            if user_info_response.status_code == 200:
                user_data = user_info_response.json().get('data', {})

                olx_id = str(user_data['id'])
                olx_user = OlxUser.objects.filter(olx_id=olx_id, olxapp=account).first()

                if olx_user:
                    # Обновление токенов для существующего пользователя
                    olx_user.access_token = access_token
                    olx_user.refresh_token = refresh_token
                    olx_user.save()

                    context = {"message": "Tokens successfully updated"}
                    return render(request, 'success.html', context, status=status.HTTP_200_OK)
                else:
                    # Создание нового пользователя
                    OlxUser.objects.create(
                        olxapp=account,
                        olx_id=olx_id,
                        email=user_data['email'],
                        name=user_data['name'],
                        phone=user_data['phone'],
                        access_token=access_token,
                        refresh_token=refresh_token
                    )

                context = {"message": "User successfully authorized"}
                return render(request, 'success.html', context, status=status.HTTP_200_OK)
            else:
                logger.error(response.json())
                context = {"error": "Failed to retrieve user information"}
                return render(request, 'error.html', context, status=status.HTTP_400_BAD_REQUEST)

        else:
            logger.error(f"Failed to obtain tokens: {response.json()}")
            context = {"error": f"{response.json()}"}
            return render(request, 'error.html', context, status=status.HTTP_400_BAD_REQUEST)
