import requests
import re

import crest, whatsapp


def connector_activate(config_value, connector, line):

    connection_data = {
        'CONNECTOR': connector,
        'LINE': line,
        'ACTIVE': 1
    }

    try:
        response = crest.call_api('POST', 'imconnector.activate', connection_data, config_value)

        # Проверка успешности ответа
        if response.get('result'):
            # Обновление конфигурации
            crest.write_to_config(config_value, {'line': line})
            return response
        else:
            print("Ошибка при активации коннектора: нет результата в ответе.")
            return response

    except Exception as e:
        print(f"Ошибка при активации коннектора: {e}")
        return False


def send_message(config_value, message_data):
    bitrix_data = crest.get_params(config_value, 'bitrix')

    # Инициализация списка файлов
    files = []
    
    # Проверка наличия ключа 'file_url' в полученных данных
    if 'file_url' in message_data:
        # Добавление URL файла в список файлов
        files.append({'url': message_data['file_url']})

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
                    'text': message_data['body'],
                    'files': files
                },
                'chat': {
                    'url': f"https://web.whatsapp.com/send/?phone={message_data['wa_id']}"
                }
            }
        ]
    }

    return crest.call_api('POST', 'imconnector.send.messages', message_data, config_value)


def send_status_delivery(config_value, status_data):

    status_data = {
        'CONNECTOR': status_data['connector_id'],
        'LINE': status_data['line_id'],
        'MESSAGES': [
            {
                'im': {
                    'chat_id': status_data['chat_id'],
                    'message_id': status_data['message_id']
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


def process_chat_message(config_value, message_data):
    # print(message_data)
    try:
        chat_id = message_data.get('data[MESSAGES][0][im][chat_id]')
        file_type =  message_data.get('data[MESSAGES][0][message][files][0][type]')
        file_link = message_data.get('data[MESSAGES][0][message][files][0][link]')
        chat_message = {}
        if not file_type:
            chat_message['type'] = 'text'
            message_text = message_data.get('data[MESSAGES][0][message][text]')
            text = re.sub(r'\[(?!(br|\n))[^\]]+\]', '', message_text)
            text = text.replace('[br]', '\n')
            chat_message['text'] = {'body': text}
        # elif file_type in ['image', 'video', 'audio']:
        elif file_type in ['image']:
            chat_message['type'] = file_type
            chat_message[file_type] = {'link': file_link}
        else:
            chat_message['type'] = 'document'
            chat_message['document'] = {}
            chat_message['document']['link'] = file_link
            chat_message['document']['filename'] = message_data.get('data[MESSAGES][0][message][files][0][name]')

        user_list = crest.call_api('GET', 'im.chat.user.list', {'CHAT_ID': chat_id}, config_value)
        get_users_info = crest.call_api('POST', 'im.user.list.get', {'ID': user_list['result']}, config_value)
        personal_mobile = get_personal_mobile(get_users_info['result'])

        for mobile in personal_mobile:
            return whatsapp.send_message(config_value, mobile, chat_message)
        
        status_data = {
            'message_id': message_data.get('data[MESSAGES][0][im][message_id]'),
            'chat_id': chat_id,
            'connector_id': message_data.get('data[CONNECTOR]'),
            'line_id': message_data.get('data[LINE]')
        }
        
        return send_status_delivery(config_value, status_data)

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



def uploadfile(config_value, file_content_base64, filename):

    bitrix_data = crest.get_params(config_value, 'bitrix')

    file_data = {
        'id': bitrix_data['storage_id'], 
        'fileContent': file_content_base64,
        'data': {'NAME': filename}
    }

    return crest.call_api('POST', 'disk.storage.uploadfile', file_data, config_value)


def imconnector_unregister(config_value, line_value):
    bitrix_data = crest.get_params(config_value, 'bitrix')
    if bitrix_data['line'] == line_value:
        connector_id = bitrix_data['connector_id']

        if crest.call_api('POST', 'imconnector.unregister', {'id': connector_id}, config_value):
            crest.write_to_config(config_value, {'line': '', 'connector_id': ''})
