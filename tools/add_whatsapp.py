import os
import json
import random
import string

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
    if not config_files:
        print("Конфигурации не найдены.")
        exit()

    config_names = []
    for filename in config_files:
        with open(os.path.join(config_folder, filename), 'r') as file:
            config = json.load(file)
            config_names.append(config['system']['config_name'])

    print("Выберите конфигурацию для подключения WhatsApp:")
    for idx, config_name in enumerate(config_names, 1):
        print(f"{idx}. {config_name}")
    
    choice = int(input("Введите номер: "))
    return config_files[choice - 1]


def choose_connector(config):
    # Проверяем, существует ли ключ 'connectors' и не пуст ли он
    if 'connectors' not in config['bitrix'] or not config['bitrix']['connectors']:
        print("нет созданных коннекторов")
        exit()

    print("Выберите коннектор:")
    for idx, connector in enumerate(config['bitrix']['connectors'], 1):
        print(f"{idx}. {connector['connector_id']}")
    choice = int(input("Введите номер: "))
    return config['bitrix']['connectors'][choice - 1]


def choose_line(connector):
    # Проверяем, существует ли ключ 'lines' и содержит ли он элементы
    if 'lines' not in connector or not connector['lines']:
        print("Не найдено подключенных линий. Подключите линию к коннектору в битрикс24")
        exit()

    print("Выберите линию:")
    for idx, line in enumerate(connector['lines'], 1):
        print(f"{idx}. {line}")
    choice = int(input("Введите номер: "))
    return connector['lines'][choice - 1]


def generate_verify_token():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=25))

def update_config(config, phone_id, connector_id, line_id, access_token, verify_token):
    whatsapp_section = {
        'phone_id': phone_id,
        'connector_id': connector_id,
        'line_id': line_id,
        'access_token': access_token,
        'verify_token': verify_token
    }

    # Убедимся, что секция messengers существует в конфиге
    if 'messengers' not in config:
        config['messengers'] = {}

    # Убедимся, что внутри messengers есть секция whatsapp
    if 'whatsapp' not in config['messengers']:
        config['messengers']['whatsapp'] = []

    # Добавляем новую секцию whatsapp
    config['messengers']['whatsapp'].append(whatsapp_section)

    # Сохраняем обновленный конфиг в файл
    with open(os.path.join(config_folder, chosen_config), 'w') as file:
        json.dump(config, file, indent=4)

config_files = read_json_files()
chosen_config = choose_configuration(config_files)

with open(os.path.join(config_folder, chosen_config), 'r') as file:
    config = json.load(file)

chosen_connector = choose_connector(config)
chosen_line = choose_line(chosen_connector)

phone_id = input("Введите ID номера телефона: ")
access_token = input("Введите access token WA Bussines: ")
verify_token = generate_verify_token()

update_config(config, phone_id, chosen_connector['connector_id'], chosen_line, access_token, verify_token)

print("1. URL обратного вызова:", f"{config['system']['domain_name']}/whatsapp?config={config['system']['config_key']}")
print("2. Подтверждение маркера:", verify_token)
