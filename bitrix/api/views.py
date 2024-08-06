from rest_framework.mixins import ListModelMixin, CreateModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework import status

from bitrix.models import Bitrix
from .serializers import PortalSerializer

from bitrix.crest import call_method
from bitrix.imconnector import register_connector
from waba.utils import send_message

import re


def get_personal_mobile(users):
    personal_mobiles = []
    for user_id, user_info in users.items():
        if user_info.get('external_auth_id') == 'imconnector':
            phones = user_info.get('phones', {})
            personal_mobile = phones.get('personal_mobile')
            if personal_mobile:
                personal_mobiles.append(personal_mobile)
    return personal_mobiles


class PortalViewSet(CreateModelMixin, GenericViewSet, ListModelMixin):
    queryset = Bitrix.objects.all()
    serializer_class = PortalSerializer

    def create(self, request, *args, **kwargs):
        try:
            event = request.data.get('event', {})
            domain = request.data.get('auth[domain]', {})
            client_endpoint = request.data.get('auth[client_endpoint]', {})
            access_token = request.data.get('auth[access_token]', {})
            refresh_token = request.data.get('auth[refresh_token]', {})
            application_token = request.data.get('auth[application_token]', {})
            api_key = request.query_params.get('api-key', {})

            if not domain:
                return Response({"error": "Domain is required"}, status=status.HTTP_400_BAD_REQUEST)
            if not access_token:
                return Response({"error": "Access token is required"}, status=status.HTTP_400_BAD_REQUEST)

            # Установка приложения
            if event == 'ONAPPINSTALL':
                data = {
                    "domain": domain,
                    "owner": request.user.id,
                    "client_endpoint": client_endpoint,
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "application_token": application_token
                }

                # Debugging the input data for serializer
                print("Serializer Input Data: ", data)

                # Create the portal with the domain and access token
                serializer = self.get_serializer(data=data)
                if not serializer.is_valid():
                    print("Serializer Errors: ", serializer.errors)
                    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

                self.perform_create(serializer)

                storage_id_data = call_method(domain, 'POST', 'disk.storage.getforapp', {})
                storage_id = storage_id_data['result']['ID']

                portal = Bitrix.objects.get(domain=domain)
                portal.storage_id = storage_id
                portal.save()

                # imconnector register
                register_connector(domain, api_key)

                headers = self.get_success_headers(serializer.data)
                return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

            # Обработка события ONIMCONNECTORMESSAGEADD
            elif event == 'ONIMCONNECTORMESSAGEADD':
                message = {}
                line = request.data.get('data[LINE]', {})
                chat_id = request.data.get('data[MESSAGES][0][im][chat_id]')
                message_id = request.data.get('data[MESSAGES][0][im][message_id]')
                message['biz_opaque_callback_data'] = f'{line}_{chat_id}_{message_id}'
                file_type = request.data.get('data[MESSAGES][0][message][files][0][type]', None)
                file_link = request.data.get('data[MESSAGES][0][message][files][0][link]', None)
                if not file_type:
                    text = request.data.get('data[MESSAGES][0][message][text]')
                    text = re.sub(r'\[(?!(br|\n))[^\]]+\]', '', text)
                    if '@#template-' in text:
                        template_name = re.search(r'@#template-(\w+)', text).group(1)
                        message['type'] = 'template'
                        message['template'] = {'name': template_name, 'language': {'code': 'en_US'}}
                    else:
                        text = text.replace('[br]', '\n')
                        message['type'] = 'text'
                        message['text'] = {'body': text}

                elif file_type in ['image']:
                    message['type'] = file_type
                    message[file_type] = {'link': file_link}

                else:
                    message['type'] = 'document'
                    message['document'] = {'link': file_link}
                    message['document']['filename'] = request.data.get('data[MESSAGES][0][message][files][0][name]')

                user_list = call_method(domain, 'POST', 'im.chat.user.list', {'CHAT_ID': chat_id})
                if user_list:
                    users = call_method(domain, 'POST', 'im.user.list.get', {'ID': user_list['result']})
                    phones = get_personal_mobile(users['result'])

                    send_message(domain, message, line, phones)

                return Response({"status": "ONIMCONNECTORMESSAGEADD event processed"}, status=status.HTTP_200_OK)

            else:
                return Response({"error": "Unsupported event"}, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            print(f"Error occurred: {str(e)}")
            return Response({"error": "Internal server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
