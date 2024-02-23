# Модуль используется при запуске рабочих скриптов из папки tools. 
import os
import sys
import json
import time

def parent_dir():
    script_directory = os.path.dirname(os.path.abspath(__file__))
    parent_directory = os.path.dirname(script_directory)
    if parent_directory not in sys.path:
        sys.path.append(parent_directory)
    return parent_directory

config_folder = os.path.join(parent_dir(), 'configs')

def load_configurations():
    configs = []
    for filename in os.listdir(config_folder):
        if filename.endswith('.json'):
            filepath = os.path.join(config_folder, filename)
            try:
                with open(filepath, 'r') as file:
                    config_data = json.load(file)
                    configs.append((filename, config_data))
            except json.JSONDecodeError as e:
                print(f"Ошибка чтения {filename}: {e}")
            except IOError as e:
                print(f"Ошибка доступа к файлу {filename}: {e}")
    return configs

def choose_configuration():
    configs = load_configurations()
    if not configs:
        print("Нет доступных конфигураций для настройки.")
        return None

    valid_configs = [config for config in configs if 'bitrix' in config[1] and 'client_id' in config[1]['bitrix'] and 'access_token' in config[1]['bitrix']]
    for idx, (filename, config) in enumerate(valid_configs, start=1):
        print(f"{idx}. {config['system']['config_name']}")

    try:
        choice = input("Выберите конфигурацию для настройки: ")
        choice = int(choice) - 1
        if 0 <= choice < len(valid_configs):
            _, selected_config = valid_configs[choice]
            return selected_config
        else:
            print("Выбран некорректный номер, попробуйте еще раз.")
    except ValueError:
        print("Пожалуйста, введите числовое значение.")


def get_time():
    return int(time.time())