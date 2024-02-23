# Скрипт регистрирует новый SMS-провайдер https://dev.1c-bitrix.ru/rest_help/messageservice/index.php
import utilities
import crest

def main():
    config_data = utilities.choose_configuration()
    if not config_data:
        return
    
    placement_handler = config_data['bitrix']['handler']
    config_value = config_data['system']['config_key']
    
    messengers = config_data.get('messengers', {})
    messenger_ids = []
    
    # Сбор всех messenger_id, где smsgate отсутствует или равен False
    for messenger_type, messenger_list in messengers.items():
        for index, messenger in enumerate(messenger_list):
            if messenger.get('smsgate', False) == False:
                messenger_id = messenger.get('messenger_id')
                if messenger_id:
                    messenger_ids.append((messenger_id, messenger_type, index))
                    
    if not messenger_ids:
        print("Мессенджеры для настройки SMS-gate не найдены.")
        return
    
    # Вывод списка для выбора
    print("Выберите мессенджер для настройки SMS-gate:")
    for idx, (messenger_id, messenger_type, _) in enumerate(messenger_ids, start=1):
        print(f"{idx}. {messenger_type}: {messenger_id}")
    
    choice = int(input("Введите номер: ")) - 1
    if 0 <= choice < len(messenger_ids):
        selected_messenger_id, selected_messenger_type, messenger_index = messenger_ids[choice]

        messageservice_name = input('Введите название (для меню): ')
        
        # Формирование и выполнение запроса
        payload = {
            'CODE': selected_messenger_id,
            'TYPE': 'SMS',
            'HANDLER': f'{placement_handler}&service=messageservice',
            'NAME': messageservice_name
        }
        
        response = crest.call_api('POST', 'messageservice.sender.add', payload, config_data)
        
        # Проверка успешности выполнения запроса
        if response.get('result'):
            print("SMS-gate успешно добавлен.")
            
            # Обновление значения smsgate в конфигурации
            messengers[selected_messenger_type][messenger_index]['smsgate'] = True
            
            if crest.write_to_config(config_value, {'messengers': messengers}, None):
                print("Конфигурация успешно обновлена с новым SMS-gate.")
            else:
                print("Ошибка при обновлении конфигурации.")
        else:
            print(f"Ошибка при добавлении SMS-gate: {response.get('error_description', 'Неизвестная ошибка')}")
    else:
        print("Неверный выбор.")

if __name__ == "__main__":
    main()
