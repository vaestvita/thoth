import os
import json

import requests


def write_to_config(config_value, app_data):
    config_path = os.path.join('configs', f"{config_value}.json")
    if os.path.exists(config_path) and config_value != 'config':
        with open(config_path, 'r') as configfile:
            config_data = json.load(configfile)
            config_data['bitrix'].update(app_data)  # Обновление данных в секции bitrix
        with open(config_path, 'w') as configfile:
            json.dump(config_data, configfile, indent=4)  # Запись обновленных данных в файл
        return True
    return False


def get_params(config_value, service):
    config_path = os.path.join('configs', f"{config_value}.json")
    if os.path.exists(config_path):
        with open(config_path, 'r') as configfile:
            config_data = json.load(configfile)
            if service in config_data:
                return config_data[service]
    return None


def get_new_token(config_name):
    try:
        bitrix_data = get_params(config_name, 'bitrix')

        new_token_data = {
            'grant_type': 'refresh_token',
            'client_id' : bitrix_data['client_id'],
            'client_secret': bitrix_data['client_secret'],
            'refresh_token': bitrix_data['refresh_token']
        }

        response = requests.get('https://oauth.bitrix.info/oauth/token/', params=new_token_data)
        response.raise_for_status()  # Проверяем, нет ли ошибок при запросе
        token_data = response.json()

        if 'access_token' in token_data and 'refresh_token' in token_data:
            # Если успешно получены access_token и refresh_token
            access_token = token_data['access_token']
            refresh_token = token_data['refresh_token']

            # Обновляем данные в файле конфигурации
            write_to_config(config_name, {'access_token': access_token, 'refresh_token': refresh_token})
            return access_token, refresh_token
        else:
            print("Не удалось получить новый токен.", token_data)
            return None, None
    except requests.exceptions.RequestException as e:
        print(f"Ошибка при выполнении запроса: {e}")
        return None, None
    except KeyError as e:
        print(f"Отсутствует ключ в данных от сервера: {e}")
        return None, None   



def call_api(method, api_method, data, config_value):
    try:
        bitrix_data = get_params(config_value, 'bitrix')
        client_endpoint = bitrix_data['client_endpoint']

        # Формирование данных для запроса
        request_data = {
            'auth': bitrix_data['access_token'],
            **data
        }

        # Выполнение запроса
        if method.upper() == 'GET':
            response = requests.get(f'{client_endpoint}{api_method}', params=request_data).json()
        elif method.upper() == 'POST':
            response = requests.post(f'{client_endpoint}{api_method}', json=request_data).json()
        else:
            return {'error': f"Unsupported HTTP method: {method}"}

        # Проверка ответа на наличие ошибки о истекшем токене
        if 'error' in response and response['error'] == 'expired_token':
            # Получаем новый токен
            access_token, refresh_token = get_new_token(config_value)
            if access_token and refresh_token:
                bitrix_data['access_token'] = access_token
                # Повторный вызов функции с обновленным токеном
                response = call_api(method, api_method, data, config_value)
                return response
            else:
                return {'error': 'Failed to get new token'}

        return response
    except Exception as e:
        return {'error': str(e)}
