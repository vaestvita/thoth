import random
import string
import base64
import requests

import utilities
import crest


def main():
    config_data = utilities.choose_configuration()
    if not config_data:
        return

    placement_handler = config_data['bitrix']['handler']
    config_value = config_data['system']['config_key']
    
    connector_name = input("Введите значение NAME коннектора: ")
    user_defined_connector_id = input("Введите id коннектора или нажмите Enter для автоматической генерации: ")
    svg_file_path_or_url = input("Введите путь к файлу SVG или URL картинки: ")
    if user_defined_connector_id.strip() == "":
        connector_id = f"{config_data['system']['config_name']}_{''.join(random.choices(string.ascii_letters + string.digits, k=5))}".lower()
    else:
        connector_id = user_defined_connector_id.strip()

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
    
    imconnector_data = {
        'ID': connector_id,
        'NAME': connector_name,
        'ICON': {
            'DATA_IMAGE': data_image
        },
        'PLACEMENT_HANDLER': placement_handler
    }

    response = crest.call_api('POST', 'imconnector.register', imconnector_data, config_data)

    if 'error' in response:
        print("Ошибка при регистрации коннектора:", response)
    elif 'result' in response and 'result' in response['result']:
        bitrix_data = config_data['bitrix']
        if 'connectors' not in bitrix_data:
            bitrix_data['connectors'] = []
        if not any(connector.get('connector_id') == connector_id for connector in bitrix_data['connectors']):
            bitrix_data['connectors'].append({'connector_id': connector_id})
        crest.write_to_config(config_value, bitrix_data, 'bitrix')
        print("Коннектор успешно зарегистрирован.")

        # Проверка и подписка
        events_to_bind = ['OnImConnectorMessageAdd', 
                        'OnImConnectorLineDelete', 
                        'OnImConnectorStatusDelete']

        # Получение списка уже зарегистрированных событий
        get_events_response = crest.call_api('POST', 'event.get', {}, config_data)

        if 'result' in get_events_response:
            # Создаем словарь, где ключи — названия событий, а значения — URL-адреса хендлеров
            registered_events = {event['event'].upper(): event['handler'] for event in get_events_response['result']}
        else:
            registered_events = {}

        for event in events_to_bind:
            event_upper = event.upper()
            event_data = {
                'event': event,
                'HANDLER': placement_handler
            }
            
            # Проверяем, зарегистрировано ли событие и совпадает ли хендлер
            if event_upper in registered_events and registered_events[event_upper] == placement_handler:
                print(f"Событие {event} уже зарегистрировано с handler {placement_handler}.")
                continue

            # Подписка на события
            response = crest.call_api('GET', 'event.bind', event_data, config_data)
        
            if 'error' in response:
                print(f"Ошибка при привязке события {event}:", response)
            else:
                message = "Событие успешно привязано." if event_upper not in registered_events else "Событие на новый handler."
                print(f"{message} {event} с handler {placement_handler}.")

    else:
        print("Не удалось обработать ответ сервера.")

if __name__ == "__main__":
    main()
