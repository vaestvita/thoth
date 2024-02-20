import os
import json
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

def get_events_input():
    events_input = input("Введите коды событий через запятую или пробел: ")
    events_list = [event.strip() for event in events_input.replace(',', ' ').split()]
    return events_list

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

    events_to_bind = get_events_input()

    get_events_response = requests.get(f'{client_endpoint}event.get', params={'auth': access_token}).json()
    registered_events = {}
    if 'result' in get_events_response:
        registered_events = {event['event'].upper(): event['handler'] for event in get_events_response['result']}

    for event in events_to_bind:
        event_upper = event.upper()
        
        if event_upper in registered_events:
            if registered_events[event_upper] == placement_handler:
                print(f"Событие {event} уже зарегистрировано с handler {placement_handler}.")
                continue
            else:
                print(f"Обновление handler для события {event}.")

        response = requests.post(f'{client_endpoint}event.bind', data={'auth': access_token, 'event': event, 'handler': placement_handler}).json()
        
        if 'error' in response:
            print(f"Ошибка при привязке события {event}: {response['error_description']}")
        else:
            print(f"Событие {event} успешно привязано к handler {placement_handler}.")

if __name__ == "__main__":
    main()
