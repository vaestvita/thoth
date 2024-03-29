import re

import crest, whatsapp


def connector_activate(config_data, placement_options):
    connector_value = placement_options.get('CONNECTOR')
    line_value = placement_options.get('LINE')
    connectors = config_data['bitrix']['connectors']

    # Поиск коннектора
    for connector_data in connectors:
        if connector_data['connector_id'] == connector_value:
            # Проверяем наличие списка lines и наличие line_value в нем
            if 'lines' in connector_data and line_value in connector_data['lines']:
                return {'error': f"Connector {connector_value} is already connected to line {line_value}."}
            
            # Если line_value отсутствует, активируем коннектор для новой линии
            connection_data = {
                'CONNECTOR': connector_value,
                'LINE': line_value,
                'ACTIVE': 1
            }
            response = crest.call_api('POST', 'imconnector.activate', connection_data, config_data)
            
            if 'result' in response:
                # Добавляем line_value в список lines
                if 'lines' not in connector_data:
                    connector_data['lines'] = []
                connector_data['lines'].append(line_value)
                config_value = config_data['bitrix']['config_key']

                # Сохраняем обновленные данные конфигурации
                crest.write_to_config(config_value, {'connectors': connectors}, 'bitrix')
                return {'Success': f"{connector_value} connected to line {line_value}."}
            return response
    else:
        # Если коннектор не найден, возвращаем ошибку
        return {'error': f"Connector {connector_value} not found in the list."}


def send_message(config_data, message_params):
    # Инициализация списка файлов
    files = []
    
    # Проверка наличия ключа 'file_url' в полученных данных
    if 'file_url' in message_params:
        # Добавление URL файла в список файлов
        files.append({'url': message_params['file_url']})

    message_data = {
        'CONNECTOR': message_params['b24_connector'],
        'LINE': message_params['b24_line'],
        'MESSAGES': [
            {
                'user': {
                    'id': message_params['wa_id'],
                    'last_name': message_params['name'],
                    'phone': message_params['wa_id'],
                    'skip_phone_validate': 'Y'
                },
                'message': {
                    'text': message_params['body'],
                    'files': files
                },
                'chat': {
                    'id': message_params['chat_id'],
                    # 'url': f"https://web.whatsapp.com/send/?phone={message_params['wa_id']}"
                }
            }
        ]
    }

    return crest.call_api('POST', 'imconnector.send.messages', message_data, config_data)


def send_status_delivery(config_data, status_data):

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

    return crest.call_api('POST', 'imconnector.send.status.delivery', status_data, config_data)    


def process_chat_message(config_data, message_data):
    try:
        connector_id = message_data.get('data[CONNECTOR]')
        line_id = message_data.get('data[LINE]')
        # Определяем мессенджер для маршрутизации
        messenger = find_messenger(config_data['messengers'], connector_id, line_id)
        if messenger:
            if messenger == 'whatsapp':
                chat_id = message_data.get('data[MESSAGES][0][im][chat_id]')
                file_type =  message_data.get('data[MESSAGES][0][message][files][0][type]')
                file_link = message_data.get('data[MESSAGES][0][message][files][0][link]')
                user_id = message_data.get('data[MESSAGES][0][message][user_id]')
                chat_message = {
                    'biz_opaque_callback_data': f'user_{user_id}'
                }
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

                user_list = crest.call_api('GET', 'im.chat.user.list', {'CHAT_ID': chat_id}, config_data)
                if user_list:
                    get_users_info = crest.call_api('POST', 'im.user.list.get', {'ID': user_list['result']}, config_data)
                personal_mobile = get_personal_mobile(get_users_info['result'])

                connector_data = {
                    'connector_id': connector_id,
                    'line_id': line_id
                }
                response =  whatsapp.send_message(config_data, personal_mobile, chat_message, connector_data)
                if not 'error' in response:
                    status_data = {
                        'message_id': message_data.get('data[MESSAGES][0][im][message_id]'),
                        'chat_id': chat_id,
                        'connector_id': connector_id,
                        'line_id': line_id
                    }

                    send_status_delivery(config_data, status_data)
                return response            
            else:
                return f'Мессенджер не найден для коннектора {connector_id} и линии {line_id}'       

    except Exception as e:
        return {'error': str(e)}


def find_messenger(messengers, connector_id, line_id):
    # Перебор всех мессенджеров в конфигурации
    for messenger_name, messenger_data in messengers.items():
        # Проверка каждой записи в списке мессенджера на совпадение с connector_id и line_id
        for entry in messenger_data:
            if entry.get('connector_id') == connector_id and str(entry.get('line_id')) == str(line_id):
                return messenger_name
    return False


def get_personal_mobile(users):
    personal_mobiles = []
    for user_id, user_info in users.items():
        if user_info.get('external_auth_id') == 'imconnector':
            phones = user_info.get('phones', {})
            personal_mobile = phones.get('personal_mobile')
            if personal_mobile:
                personal_mobiles.append(personal_mobile)
    return personal_mobiles


def uploadfile(config_data, file_content_base64, filename):
    bitrix_data = config_data['bitrix']
    file_data = {
        'id': bitrix_data['storage_id'], 
        'fileContent': file_content_base64,
        'data': {'NAME': filename}
    }

    return crest.call_api('POST', 'disk.storage.uploadfile', file_data, config_data)


def get_storage(config_data):
    config_value = config_data['bitrix']['config_key']
    get_storage_data = crest.call_api('POST', 'disk.storage.getforapp', {}, config_data)
    if 'result' in get_storage_data:
        storage_id = get_storage_data['result']['ID']
        if crest.write_to_config(config_value, {'storage_id': storage_id}, 'bitrix'):
            return f'ID {storage_id} хранилища успешно записан в конфигурацию'
    else:
        return f'Ошибка получения данных хранилища {get_storage_data}'


def line_disconnection(config_data, event_data):
    bitrix_data = config_data['bitrix']
    event_value = event_data.get('event')
    line_value = event_data.get('data[line]')
    connector_value = event_data.get('data[connector]')
    connectors = bitrix_data['connectors']
    
    if event_value == 'ONIMCONNECTORSTATUSDELETE':
        # Удаляем line_value только из конкретного коннектора
        for connector in connectors:
            if connector['connector_id'] == connector_value and 'lines' in connector:
                if line_value in connector['lines']:
                    connector['lines'].remove(line_value)
                    response = f"Line {line_value} disconnected from connector {connector_value}."
    
    elif event_value == 'ONIMCONNECTORLINEDELETE':
        # Удаляем line_value из всех коннекторов
        for connector in connectors:
            if 'lines' in connector and line_value in connector['lines']:
                connector['lines'].remove(line_value)
                response = f"Line {line_value} disconnected from all connectors."

    # Сохранение обновленных данных конфигурации
    config_value = bitrix_data['config_key']
    if crest.write_to_config(config_value, {'connectors': connectors}, 'bitrix'):
        return response


def messageservice_processing(config_data, message_data):
    messageservice_code = message_data.get('code')
    if messageservice_code:
        messenger_type, whatsapp_data = get_messenger_type_by_id(config_data, messageservice_code)
        if not messenger_type:
            print('Messenger not found')
            return
        message_to = message_data.get('message_to')
        message_body = message_data.get('message_body')
        user_id = message_data.get('auth[user_id]')
        if messenger_type == 'whatsapp' and whatsapp_data:
            message = {
                'type': 'text',
                'text': {
                    'body': message_body
                },
                'biz_opaque_callback_data': f'user_{user_id}'
            }
            whatsapp.send_message(config_data, [message_to], message, whatsapp_data=whatsapp_data)
        else:
            print(f'Messenger type {messenger_type} is not supported or whatsapp_data is missing')


def get_messenger_type_by_id(config_data, messenger_id):
    messengers = config_data.get('messengers', {})
    for messenger_type, messenger_list in messengers.items():
        for messenger in messenger_list:
            if messenger.get('messenger_id') == messenger_id and messenger_type == "whatsapp":
                whatsapp_data = {
                    "access_token": messenger.get("access_token"),
                    "phone_id": messenger.get("phone_id")
                }
                return messenger_type, whatsapp_data
            elif messenger.get('messenger_id') == messenger_id:
                # Для неватсап мессенджеров возвращаем только тип
                return messenger_type, None
    return None, None


def send_notification(config_data, data):


    notification_data = {

        **data,
        'ATTACH': []
    }

    crest.call_api('POST', 'im.notify.system.add', notification_data, config_data)


# Интеграция с Asterisk

import configparser
import json
import time

config = configparser.ConfigParser()
config.read('config.ini')

CONFIG_FILE = config.get('bitrix', 'config_value')
CONFIG_DATA = crest.get_params(CONFIG_FILE)
BITRIX_USERS_FILE = 'bitrix_users.json'
DEFAULT_USER_ID = config.get('bitrix', 'default_user_id')
CRM_CREATE = config.get('bitrix', 'crm_create')
SHOW_CARD = config.get('bitrix', 'show_card')


def update_bitrix_users_file():
    start = 0
    bitrix_users = {}

    while True:
        response = crest.call_api('POST', 'user.get', {'ACTIVE': 'true', 'start': start}, CONFIG_DATA)
        if 'result' in response:
            users = response['result']
            for user in users:
                if user.get('UF_PHONE_INNER'):
                    bitrix_users[user.get('ID')] = user.get('UF_PHONE_INNER')
            start += len(users)
            if 'next' not in response:
                break
        else:
            print('Ошибка при получении списка пользователей', response)
            break

    with open(BITRIX_USERS_FILE, 'w') as file:
        json.dump(bitrix_users, file)


def get_user_info(user_id=None, user_phone=None):
    for _ in range(2):
        try:
            with open(BITRIX_USERS_FILE, 'r') as file:
                bitrix_users = json.load(file)
        except Exception:
            bitrix_users = {}
            update_bitrix_users_file()
            continue

        if user_phone:
            for key, value in bitrix_users.items():
                if value == user_phone:
                    return key, False

        if user_id:
            if user_id in bitrix_users:
                return bitrix_users[user_id], False

        break

    default_value = DEFAULT_USER_ID if DEFAULT_USER_ID else next(iter(bitrix_users.keys()), None)
    return default_value, True


# Регистрация звонка в Битрикс24
def register_call(bitrix_user_id, phone_number, call_type):
    register_param = {
        'USER_ID': bitrix_user_id,
        'PHONE_NUMBER': phone_number,
        'TYPE': call_type,
        'SHOW': SHOW_CARD,
        'CRM_CREATE': CRM_CREATE
    }

    call_data = crest.call_api('POST', 'telephony.externalcall.register', register_param, CONFIG_DATA)
    if 'result' in call_data:
        return call_data['result']['CALL_ID']
    else:
        print('ОШИБКА!!!!! register_call', phone_number, call_data)


# Завершение звонка
def finish_call(call_data, config_data=None):
    finish_param = {
        'CALL_ID': call_data.get('bitrix_call_id'),
        'USER_ID': call_data.get('bitrix_user_id'),
        'DURATION': round(time.time() - call_data.get('start_time', time.time())),
        'STATUS_CODE': call_data.get('call_status')
    }

    if None in finish_param.values():  # Проверяем, есть ли None среди значений
        print('Один из параметров равен None')
        return False

    config_to_use = config_data if config_data is not None else CONFIG_DATA
    response = crest.call_api('POST', 'telephony.externalcall.finish', finish_param, config_to_use)
    if 'result' in response:
        return True
    else:
        print('ОШИБКА finish_call', response)
        return False


# Отправка файла записи
def attachRecord(call_data, encoded_file):
    file_data = {
        'CALL_ID': call_data["bitrix_call_id"],
        'FILENAME': call_data["file_name"],
        'FILE_CONTENT': encoded_file
    }

    response = crest.call_api('POST', 'telephony.externalCall.attachRecord', file_data, CONFIG_DATA)


# Показать/скрыть карточку
def card_action(call_id, user_id, action, config_data=None):
    if SHOW_CARD != '1' and action == 'show':
        return

    call_data = {
        'CALL_ID': call_id,
        'USER_ID': user_id
    }
    config_to_use = config_data if config_data is not None else CONFIG_DATA

    response = crest.call_api('POST', f'telephony.externalcall.{action}', call_data, config_to_use)