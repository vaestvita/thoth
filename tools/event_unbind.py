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

def list_events(client_endpoint, access_token):
    response = requests.get(f'{client_endpoint}event.get', params={'auth': access_token}).json()
    if 'result' in response:
        events = response['result']
        for idx, event in enumerate(events, 1):
            print(f"{idx}. {event['event']} - {event['handler']}")
        return events
    else:
        print(f"Не удалось получить список событий. {response['error']}")
        return []

def get_event_numbers():
    numbers_input = input("Введите номера событий для удаления через запятую или пробел: ")
    numbers = [int(number.strip()) for number in numbers_input.replace(',', ' ').split()]
    return numbers

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

    events = list_events(client_endpoint, access_token)
    if not events:
        return
    
    event_numbers = get_event_numbers()
    for number in event_numbers:
        if number <= len(events) and number > 0:
            event = events[number - 1]
            response = requests.post(f'{client_endpoint}event.unbind', data={'auth': access_token, 'event': event['event'], 'handler': event['handler']}).json()
            if 'result' in response:
                print(f"Ответ сервера по событию {event['event']}: {response['result']}")
            elif 'error' in response:
                print(f"Ответ сервера по событию {event['event']}: {response['error']}")
        else:
            print(f"Неверный номер события: {number}")

if __name__ == "__main__":
    main()
