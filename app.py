from flask import Flask, request, jsonify
import os
import json

import crest, bitrix, whatsapp


def check_config_value(config_value, service, bitrix24_domain=None):    
    config_path = os.path.join('configs', f"{config_value}.json")    
    if os.path.exists(config_path) and config_value != 'config':
        with open(config_path, 'r') as configfile:
            config_data = json.load(configfile)            
            if service == 'bitrix':                
                if 'bitrix24_domain' in config_data['system'] and bitrix24_domain:
                    return config_data['system']['bitrix24_domain'] == bitrix24_domain
                else:
                    return False
            else:
                return True                
    return False


app = Flask(__name__)


@app.route('/', methods=['GET', 'POST'])
def project_info():
    if request.method == 'GET' or request.method == 'POST':
        info = {
            'App': {
                'Name': 'Bitrix24 Integration Hub - Thoth',
                'URL': 'https://github.com/vaestvita/thoth'
            },
            'Developer': {
                'Name': 'Anton Gulin',
                'Phone': '+7 705 864 55 43',
                'Mail': 'antgulin@ya.ru'
            }
        }
        return jsonify(info)


@app.route('/install', methods=['POST'])
def app_install():
    event_value = request.form.get('event') == 'ONAPPINSTALL'
    config_value = request.args.get('config')
    bitrix24_domain = request.form.get('auth[domain]')
    if event_value and config_value and check_config_value(config_value, 'bitrix', bitrix24_domain):

        app_data = {
            'member_id': request.form.get('auth[member_id]'),
            'access_token': request.form.get('auth[access_token]'),
            'refresh_token': request.form.get('auth[refresh_token]'),
            'client_endpoint': request.form.get('auth[client_endpoint]'),
            'server_endpoint': request.form.get('auth[server_endpoint]'),
            'application_token': request.form.get('auth[application_token]'),
            'scope': request.form.get('auth[scope]'),
            'status': request.form.get('auth[status]'),
        }

        if crest.write_to_config(config_value, app_data):
            return 'Success', 200
        else:
            return 'Error writing to config', 500
    else:
        return 'Forbidden', 403
    

@app.route('/bitrix', methods=['POST'])
def b24_handler():
    
    config_value = request.args.get('config')
    bitrix24_domain = request.args.get('DOMAIN') or request.form.get('auth[domain]')
    if config_value and check_config_value(config_value, 'bitrix', bitrix24_domain):
        
        placement_value = request.form.get('PLACEMENT')
        if placement_value and placement_value == 'SETTING_CONNECTOR':
            placement_options = json.loads(request.form.get('PLACEMENT_OPTIONS', '{}'))
            connector_value = placement_options.get('CONNECTOR')
            line_value = placement_options.get('LINE')
            return bitrix.connector_activate(config_value, connector_value, line_value)

        event_value = request.form.get('event')
        if event_value:
            if  event_value == 'ONIMCONNECTORMESSAGEADD':
                chat_id = request.form.get('data[MESSAGES][0][im][chat_id]')
                message_id = request.form.get('data[MESSAGES][0][im][message_id]')
                chat_message = request.form.get('data[MESSAGES][0][message][text]')
                bitrix.send_status_delivery(config_value, chat_id, message_id)
                bitrix.process_chat_message(config_value, chat_id, chat_message)

            # При отключении коннектора от линии очистка значнеия в конфиге
            elif event_value == 'ONIMCONNECTORSTATUSDELETE':
                # line_value = request.form.get('data[line]')
                # crest.write_to_config(config_value, {'line': ''})
                pass

            # При удалении линии, удалить коннектор
            elif event_value == 'ONIMCONNECTORLINEDELETE':
                line_value = request.form.get('data')
                bitrix.imconnector_unregister(config_value, line_value)
                pass                
       
            return 'Success', 200
    return 'Forbidden', 403
        

@app.route('/whatsapp', methods=['GET', 'POST'])
def wba_handler():
    if request.method == 'GET':
        config_value = request.args.get('config')
        if config_value and check_config_value(config_value, 'whatsapp'):
            if request.args.get("hub.mode") == 'subscribe':
                verify_token = request.args.get("hub.verify_token")
                if whatsapp.webhook_subscribe(config_value, verify_token):
                    challenge = request.args.get("hub.challenge")
                    return challenge, 200
                
        return 'Forbidden', 403
                
    elif request.method == 'POST':
        
        config_value = request.args.get('config')
        if config_value and check_config_value(config_value, 'whatsapp'):
           response = whatsapp.message_processing(request.json['entry'][0], config_value)
           return 'Success', 200
        return 'Forbidden', 403


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000)