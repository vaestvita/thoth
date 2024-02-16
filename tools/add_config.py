import os
import random
import string
import json

def generate_random_string(length):
    """Генерация случайной строки из цифр и латинских букв"""
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

def create_config_file(domain_name, config_name, bitrix24_domain):
    """Создание файла конфигурации и добавление данных"""
    config_file = generate_random_string(20)
    script_directory = os.path.dirname(os.path.abspath(__file__))
    parent_directory = os.path.dirname(script_directory)
    config_folder = os.path.join(parent_directory, 'configs')
    config_path = os.path.join(config_folder, config_file + '.json') 
    
    if not os.path.exists(config_folder):
        os.makedirs(config_folder)
    
    config_data = {
        'system': {
            'config_name': config_name, 
            'domain_name': domain_name, 
            'config_key': config_file, 
            'bitrix24_domain': bitrix24_domain
            },
        'bitrix': {
            'client_id': '', 'client_secret': '', 
            'handler': f'{domain_name}/bitrix?config={config_file}',
                   },
        'whatsapp': {
            'verify_token': generate_random_string(25), 
            'access_token': '',
            'phone_number_id': ''
            }
    }
    
    with open(config_path, 'w') as configfile:
        json.dump(config_data, configfile, indent=4) 
    return config_file, config_data['whatsapp']['verify_token']

def main():
    config_name = input("Введите название конфигурации (my_project): ")
    bitrix24_domain = input("Введите адрес портала (domain.bitrix24.ru): ")
    domain_name = input("Введите домен сервера, где будет расположен скрипт (domain.ru): ")
    domain_name = 'https://' + domain_name if not domain_name.startswith('https://') else domain_name
    
    config_file, verify_token = create_config_file(domain_name, config_name, bitrix24_domain)
    
    print("Базовая конфигурация сохранена. Данные для регистрации приложения:")
    print(f"1. Битрикс24. Путь вашего обработчика: {domain_name}/bitrix?config={config_file}")
    print(f"2. Битрикс24. Путь для первоначальной установки: {domain_name}/install?config={config_file}")
    print(f"3. Whatsapp. URL обратного вызова: {domain_name}/whatsapp?config={config_file}")
    print(f"4. Whatsapp. Подтверждение маркера: {verify_token}")

if __name__ == "__main__":
    main()
