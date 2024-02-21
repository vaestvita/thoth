import random
import string

import utilities
import crest

def choose_connector(config_data):
    connectors = config_data['bitrix'].get('connectors', [])
    if not connectors:
        print("нет созданных коннекторов")
        return None

    for idx, connector in enumerate(connectors, 1):
        print(f"{idx}. {connector['connector_id']}")
    try:
        choice = int(input("Выебрите коннектор: ")) - 1
        if 0 <= choice < len(connectors):
            return connectors[choice]
    except ValueError:
        pass
    print("Некорректный ввод.")
    return None


def choose_line(connector):
    lines = connector.get('lines', [])
    if not lines:
        print("Не найдено подключенных линий. Подключите линию к коннектору в интерфейсе битрикс24")
        return None

    for idx, line in enumerate(lines, 1):
        print(f"{idx}. {line}")
    try:
        choice = int(input("Выберите линию: ")) - 1
        if 0 <= choice < len(lines):
            return lines[choice]
    except ValueError:
        pass
    print("Некорректный ввод.")
    return None


def generate_verify_token():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=25))

def update_config(config_data, whatsapp_data):
    config_value = config_data['system']['config_key']
    # Убедимся, что секция messengers существует в конфиге
    if 'messengers' not in config_data:
        config_data['messengers'] = {}
    messengers = config_data['messengers']

    # Убедимся, что внутри messengers есть секция whatsapp
    if 'whatsapp' not in messengers:
        messengers['whatsapp'] = []

    # Добавляем новую секцию whatsapp
    messengers['whatsapp'].append(whatsapp_data)

    crest.write_to_config(config_value, messengers, 'messengers')

def main():
    config_data = utilities.choose_configuration()
    if not config_data:
        return    
    chosen_connector = choose_connector(config_data)
    if not chosen_connector:
        return
    chosen_line = choose_line(chosen_connector)
    if not chosen_line:
        return
    phone_id = input("Введите ID номера телефона: ")
    access_token = input("Введите access token WA Bussines: ")
    verify_token = generate_verify_token()
    whatsapp_data = {
        'phone_id': phone_id,
        'connector_id': chosen_connector['connector_id'],
        'line_id': chosen_line,
        'access_token': access_token,
        'verify_token': verify_token
    }

    update_config(config_data, whatsapp_data)

    print("1. URL обратного вызова:", f"{config_data['system']['domain_name']}/whatsapp?config={config_data['system']['config_key']}")
    print("2. Подтверждение маркера:", verify_token)

if __name__ == "__main__":
    main()