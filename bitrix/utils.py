import os
import re
import base64
import json
from rest_framework import status
from rest_framework.response import Response

from waba.utils import send_message

from thoth.settings import env
from .models import Bitrix
from waba.models import Waba, Phone

from .crest import call_method

HOME_URL = env('HOME_URL')
EVENTS = ['ONIMCONNECTORMESSAGEADD', 'ONIMCONNECTORLINEDELETE', 'ONIMCONNECTORSTATUSDELETE']



def thoth_logo():
    dir = os.path.dirname(os.path.abspath(__file__))
    waba_logo = os.path.join(dir, 'img', 'WhatsApp.svg')

    with open(waba_logo, 'rb') as file:
        image_data = file.read()
        encoded_image = base64.b64encode(image_data).decode('utf-8')
        return f"data:image/svg+xml;base64,{encoded_image}"
    

# Регистрация коннектора
def register_connector(domain, api_key):

    payload = {
        'ID': 'thoth_waba',
        'NAME': 'THOTH WABA',
        'ICON': {
            'DATA_IMAGE': thoth_logo()
        },
        'PLACEMENT_HANDLER': f'{HOME_URL}/api/bitrix/?api-key={api_key}'
    }

    call_method(domain, 'POST', 'imconnector.register', payload)

    # Подписка на события
    for event in EVENTS:

        payload = {
            'event': event,
            'HANDLER': f'{HOME_URL}/api/bitrix/?api-key={api_key}'
        }

        call_method(domain, 'POST', 'event.bind', payload)


# Регистрация SMS-провайдера
def messageservice_add(domain, phone, line, api_key):

    payload = {
        'CODE': f'THOTH_WABA_{phone}_{line}',
        'NAME': f'THOTH WABA ({phone})',
        'TYPE': 'SMS',
        'HANDLER': f'{HOME_URL}/api/bitrix/?api-key={api_key}'
    }

    return call_method(domain, 'POST', 'messageservice.sender.add', payload)



def get_personal_mobile(users):
    personal_mobiles = []
    for user_id, user_info in users.items():
        if user_info.get('external_auth_id') == 'imconnector':
            phones = user_info.get('phones', {})
            personal_mobile = phones.get('personal_mobile')
            if personal_mobile:
                personal_mobiles.append(personal_mobile)
    return personal_mobiles



def event_processor(self, request):
    try:
        event = request.data.get('event', {})
        domain = request.data.get('auth[domain]', {})
        client_endpoint = request.data.get('auth[client_endpoint]', {})
        access_token = request.data.get('auth[access_token]', {})
        refresh_token = request.data.get('auth[refresh_token]', {})
        application_token = request.data.get('auth[application_token]', {})
        api_key = request.query_params.get('api-key', {})
        placement_options = request.data.get('PLACEMENT_OPTIONS', {})
        sms_msg = request.data.get('type', {})

        if placement_options:
            placement_options = json.loads(placement_options)
            domain = request.query_params.get('DOMAIN', {})
            line = placement_options.get('LINE')
            line_data = call_method(domain, 'POST', 'imopenlines.config.get', {'CONFIG_ID': line})
            if 'result' in line_data:
                _, phone_number = line_data['result']['LINE_NAME'].split('_')
                phone = Phone.objects.filter(phone=phone_number).first()
                if phone:
                    phone.line = line
                    phone.save()

                    payload = {
                        'CONNECTOR': placement_options.get('CONNECTOR'),
                        'LINE': line,
                        'ACTIVE': 1
                    }

                    call_method(domain, 'POST', 'imconnector.activate', payload)

            return Response({"status": "message processed"}, status=status.HTTP_200_OK)
        
        if not domain:
            return Response({"error": "Domain is required"}, status=status.HTTP_400_BAD_REQUEST)
        if not access_token:
            return Response({"error": "Access token is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Проверка наличия домена в базе данных
        try:
            portal = Bitrix.objects.get(domain=domain)
            # Обновление access_token
            portal.access_token = access_token
            portal.save()
        except Bitrix.DoesNotExist:
            # Если событие ONAPPINSTALL, сохраняем данные домена в базу
            if event == 'ONAPPINSTALL':
                data = {
                    "domain": domain,
                    "owner": request.user.id,
                    "client_endpoint": client_endpoint,
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "application_token": application_token
                }

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
            else:
                return Response({"error": "Domain not found and not an install event"}, status=status.HTTP_400_BAD_REQUEST)

        # Messages from SMS gate
        if sms_msg == 'SMS':
            phones = []
            message_to = request.data.get('message_to', {})
            phones.append(message_to)
            template, language = request.data.get('message_body', {}).split('+')
            message = {
                'type': 'template',
                'template': {'name': template, 'language': {'code': language}}
            }
            code = request.data.get('code', {})
            line = re.search(r'_(\d+)$', code).group(1)

            send_message(domain, message, line, phones)
            return Response({"status": "message processed"}, status=status.HTTP_200_OK)

        # Обработка события ONIMCONNECTORMESSAGEADD
        if event == 'ONIMCONNECTORMESSAGEADD':
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
                if 'template-' in text:
                    _, template_body = text.split('-')
                    template, language = template_body.split('+')
                    message['type'] = 'template'
                    message['template'] = {'name': template, 'language': {'code': language}}
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

        
        elif event == 'ONIMCONNECTORSTATUSDELETE':
            line = request.data.get('data[line]')
            phone = Phone.objects.filter(waba__bitrix__domain=domain, line=line).first()
            if phone:
                phone.line = ''
                phone.save()
                return Response({"status": "Line cleared"}, status=status.HTTP_200_OK)
            else:
                return Response({"error": "Line not found"}, status=status.HTTP_404_NOT_FOUND)
        
        else:
            return Response({"error": "Unsupported event"}, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        print(f"Error occurred: {str(e)}")
        return Response({"error": "Internal server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)