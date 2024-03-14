from flask import Flask, request, jsonify
import json
import logging
from logging.handlers import TimedRotatingFileHandler
import os
import configparser

import threading
import asyncio


config_file = 'config.ini'
config = configparser.ConfigParser()

# Проверка, существует ли файл конфигурации
if not os.path.exists(config_file):
    config['asterisk'] = {'enabled': 'False'}
    config['bitrix'] = {'config_value': '', 'default_user_id': '', 'crm_create': 0, 'show_card': 0}
    with open(config_file, 'w') as configfile:
        config.write(configfile)
else:
    config.read(config_file)

import bitrix, crest, whatsapp

# Подключение к Asterisk
if config.getboolean('asterisk', 'enabled'):

    from asterisk import manager
    import asterisk

    def run_ami_manager():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        loop.run_until_complete(
            manager.connect(run_forever=True)
        )
    ami_thread = threading.Thread(target=run_ami_manager, daemon=True)
    ami_thread.start()
    print(' * Asterisk manager started')


log_directory = "logs"
if not os.path.exists(log_directory):
    os.makedirs(log_directory)

log_file_path = os.path.join(log_directory, "app.log")
logger = logging.getLogger("MyLogger")
logger.setLevel(logging.INFO)  
handler = TimedRotatingFileHandler(log_file_path, when="midnight", interval=1, backupCount=30)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


def check_config_value(config_value, section=None, bitrix24_domain=None):
    config_data = crest.get_params(config_value)
    if config_data:
        if section == 'bitrix':
            if bitrix24_domain == config_data['bitrix']['bitrix24_domain']:
                return config_data
            else:
                return False
        else:
            return config_data
    return False


app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def project_info():
    if request.method == 'GET' or request.method == 'POST':
        info = {
            'App': {
                'Name': 'Thoth: Bitrix24 Integration Hub',
                'URL': 'https://github.com/vaestvita/thoth'
            },
            'Developer': {
                'Name': 'Anton Gulin',
                'Phone': '+7 705 864 55 43',
                'Mail': 'antgulin@ya.ru'
            }
        }
        return jsonify(info)


@app.route('/bitrix', methods=['POST'])
def b24_handler():
    config_value = request.args.get('config')
    bitrix24_domain = request.args.get('DOMAIN') or request.form.get('auth[domain]')

    if not config_value:
        return 'Forbidden', 403
    config_data = check_config_value(config_value, 'bitrix', bitrix24_domain)
    if not config_data:
        return 'Forbidden', 403

    # Обработка PLACEMENT
    placement_value = request.form.get('PLACEMENT')
    if placement_value and placement_value == 'SETTING_CONNECTOR':
        placement_options = json.loads(request.form.get('PLACEMENT_OPTIONS', '{}'))            
        response = bitrix.connector_activate(config_data, placement_options)
        logger.info(response)
        return response

    # Обработка событий
    event_value = request.form.get('event')
    # Установка приложения
    if event_value == 'ONAPPINSTALL':
        app_data = {
            'app_admin_id': request.form.get('auth[user_id]'),
            'member_id': request.form.get('auth[member_id]'),
            'access_token': request.form.get('auth[access_token]'),
            'refresh_token': request.form.get('auth[refresh_token]'),
            'client_endpoint': request.form.get('auth[client_endpoint]'),
            'server_endpoint': request.form.get('auth[server_endpoint]'),
            'application_token': request.form.get('auth[application_token]'),
            'scope': request.form.get('auth[scope]'),
            'status': request.form.get('auth[status]'),
        }

        if crest.write_to_config(config_value, app_data, 'bitrix'):
            config_data['bitrix'].update(app_data)
            storage_data = bitrix.get_storage(config_data)
            logger.info(storage_data)
            return 'Success', 200
        else:
            return 'Error writing to config', 500

    # Обработка сообщений из CRM
    elif event_value == 'ONIMCONNECTORMESSAGEADD':
        response = bitrix.process_chat_message(config_data, request.form)
        logger.info(f'ONIMCONNECTORMESSAGEADD{response}')
        
    # При отключении или удалении от линии удалить линию из списка линий коннектора
    elif event_value in ['ONIMCONNECTORSTATUSDELETE', 'ONIMCONNECTORLINEDELETE']:
        response = bitrix.line_disconnection(config_data, request.form)
        logger.info(response)

    # Событие ClickToCall
    elif event_value == 'ONEXTERNALCALLSTART':
        user_id = request.form.get('data[USER_ID]')
        call_id = request.form.get('data[CALL_ID]')
        # Если Asterisk не подключен
        if not config.getboolean('asterisk', 'enabled'):
            # закрыть карточку
            bitrix.card_action(call_id, user_id, 'hide', config_data)

            # завершить звонок
            call_data = {
                'bitrix_call_id': call_id,
                'bitrix_user_id': user_id,
                'call_status': 403
            }
            bitrix.finish_call(call_data, config_data)

            # Отправить уведомление
            message_data = {
                'MESSAGE': 'Asterisk не подключен. <br> Обратитесь в поддержку <a href="https://app.thoth.kz">app.thoth</a>',
                'TO': user_id
            }
            bitrix.send_notification(config_data, message_data)
            return 'Asterisk is not enabled', 500
        extension, default = bitrix.get_user_info(user_id=user_id)
        phone_num = request.form.get('data[PHONE_NUMBER]')
        if not default:
            asyncio.run(asterisk.initiate_call(extension, phone_num, call_id, user_id))

    else:
        print(request.form)
    
    service_value = request.args.get('service')
    # Обработка SMS сообщений 
    if service_value and service_value == 'messageservice':
        bitrix.messageservice_processing(config_data, request.form)
    return 'Success', 200


@app.route('/whatsapp', methods=['GET', 'POST'])
def wba_handler():
    config_value = request.args.get('config')
    if not config_value:
        return 'Forbidden', 403
    config_data = check_config_value(config_value)
    if not config_data:
        return 'Forbidden', 403
    if request.method == 'GET':    
        if request.args.get("hub.mode") == 'subscribe':
            verify_token = request.args.get("hub.verify_token")
            if whatsapp.webhook_subscribe(config_data, verify_token):
                challenge = request.args.get("hub.challenge")
                return challenge, 200
            else:
                return 'Forbidden', 403
                
    elif request.method == 'POST':
        response = whatsapp.message_processing(request.json['entry'][0], config_data)
        logger.info(response)
        return 'Success', 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000, use_reloader=False)