import requests

import crest, whatsapp


def connector_activate(config_value, connector, line):

    connection_data = {
        'CONNECTOR': connector,
        'LINE': line,
        'ACTIVE': 1
    }

    response =  crest.call_api('POST', 'imconnector.activate', connection_data, config_value)

    # Если ответ успешный, обновляем значение line в файле конфигурации
    if response['result']:
        crest.write_to_config(config_value, {'line': line})

    return response


def send_message(config_value, message_data):
    bitrix_data = crest.get_params(config_value, 'bitrix')

    message_data = {
        'CONNECTOR': bitrix_data['connector_id'],
        'LINE': bitrix_data['line'],
        'MESSAGES': [
            {
                'user': {
                    'id': message_data['wa_id'],
                    'last_name': message_data['name'],
                    'phone': message_data['wa_id'],
                    'skip_phone_validate': 'Y'
                },
                'message': {
                    'text': message_data['body']
                },
                'chat': {
                    'url': f"https://web.whatsapp.com/send/?phone={message_data['wa_id']}"
                }
            }
        ]
    }

    return crest.call_api('POST', 'imconnector.send.messages', message_data, config_value)


def send_status_delivery(config_value, chat_id, message_id):
    bitrix_data = crest.get_params(config_value, 'bitrix')

    status_data = {
        'CONNECTOR': bitrix_data['connector_id'],
        'LINE': bitrix_data['line'],
        'MESSAGES': [
            {
                'im': {
                    'chat_id': chat_id,
                    'message_id': message_id
                },
                'message': {
                    'id': []
                },
                'chat': {
                    'id': ''
                }
            }
        ]
    }

    return crest.call_api('POST', 'imconnector.send.status.delivery', status_data, config_value)    


def process_chat_message(config_value, chat_id, chat_message):
    try:
        bitrix_data = crest.get_params(config_value, 'bitrix')
        client_endpoint = bitrix_data['client_endpoint']
        access_token = bitrix_data['access_token']

        user_list = requests.get(f'{client_endpoint}im.chat.user.list?auth={access_token}&CHAT_ID={chat_id}').json()

        payload = {
            'auth': access_token,
            'ID': user_list['result']
        }

        get_users_info = requests.post(f'{client_endpoint}im.user.list.get', json=payload).json()
        personal_mobile = get_personal_mobile(get_users_info['result'])

        for mobile in personal_mobile:
            whatsapp.send_message(config_value, mobile, chat_message)

    except Exception as e:
        return {'error': str(e)}


def get_personal_mobile(users):
    personal_mobiles = []
    for user_id, user_info in users.items():
        if user_info.get('external_auth_id') == 'imconnector':
            phones = user_info.get('phones', {})
            personal_mobile = phones.get('personal_mobile')
            if personal_mobile:
                personal_mobiles.append(personal_mobile)
    return personal_mobiles