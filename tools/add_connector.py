import os
import json
import random
import string
import base64
import requests


script_directory = os.path.dirname(os.path.abspath(__file__))
parent_directory = os.path.dirname(script_directory)
config_folder = os.path.join(parent_directory, 'configs')

def read_json_files():
    config_files = []
    for filename in os.listdir(config_folder):
        if filename.endswith('.json'):
            config_files.append(filename)
    return config_files

def choose_configuration(config_files):
    print("Выберите номер конфигурации для настройки:")
    for idx, filename in enumerate(config_files, 1):
        with open(os.path.join(config_folder, filename), 'r') as file:
            file_data = json.load(file)
            if 'bitrix' in file_data and 'client_id' in file_data['bitrix'] and 'access_token' in file_data['bitrix']:
                print(f"{idx}. {file_data['system']['config_name']}")
    choice = int(input("Введите номер: "))
    return config_files[choice - 1]

def main():
    config_files = read_json_files()
    if not config_files:
        print("Нет доступных конфигураций для настройки.")
        return
    
    chosen_config = choose_configuration(config_files)

    chosen_file_path = os.path.join(config_folder, chosen_config)
    
    with open(chosen_file_path, 'r') as file:
        file_data = json.load(file)
        client_endpoint = file_data['bitrix']['client_endpoint']
        access_token = file_data['bitrix']['access_token']
        placement_handler = file_data['bitrix']['handler']
    
    connector_name = input("Введите значение NAME коннектора: ")
    svg_file_path_or_url = input("Введите путь к файлу SVG или URL картинки: ")
    
    if svg_file_path_or_url.startswith('http://') or svg_file_path_or_url.startswith('https://'):
        # Скачивание изображения по URL
        response = requests.get(svg_file_path_or_url)
        if response.status_code != 200:
            print("Ошибка при загрузке изображения по URL:", response.status_code)
            return
        image_data = response.content
    else:
        # Чтение локального файла
        with open(svg_file_path_or_url, 'rb') as svg_file:
            image_data = svg_file.read()
    
    # Конвертация изображения в base64
    encoded_image = base64.b64encode(image_data).decode('utf-8')
    data_image = f"data:image/svg+xml;base64,{encoded_image}"
    
    connector_id = f"{file_data['system']['config_name']}_{''.join(random.choices(string.ascii_letters + string.digits, k=5))}"
    
    imconnector_data = {
        'auth': access_token,
        'ID': connector_id,
        'NAME': connector_name,
        'ICON': {
            'DATA_IMAGE': data_image
        },
        'PLACEMENT_HANDLER': placement_handler
    }

    response = requests.post(f'{client_endpoint}imconnector.register', json=imconnector_data).json()
    
    if 'error' in response:
        print("Ошибка при регистрации коннектора:", response)
    elif 'result' in response and 'result' in response['result']:
        file_data['bitrix']['connector_id'] = connector_id
        with open(chosen_file_path, 'w') as file:
            json.dump(file_data, file, indent=4)
        print("Коннектор успешно зарегистрирован.")
        
        event_data = {
            'auth': access_token,
            'event': 'OnImConnectorMessageAdd',
            'HANDLER': placement_handler
        }
        
        response = requests.get(f'{client_endpoint}event.bind.json', params=event_data).json()
        if 'error' in response:
            print("Ошибка при привязке события:", response)
        else:
            print("Событие OnImConnectorMessageAdd успешно привязано.")
    else:
        print("Не удалось обработать ответ сервера.")

if __name__ == "__main__":
    main()
