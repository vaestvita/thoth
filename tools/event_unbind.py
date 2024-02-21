import utilities
import crest

def list_events(config_data):
    response = crest.call_api('POST', 'event.get', {}, config_data)    
    if 'result' not in response:
        print(f"Не удалось получить список событий. {response.get('error', 'Неизвестная ошибка')}")
        return []    
    if not response['result']:
        print("Подписок на события не найдено.")
        return []    
    events = response['result']
    for idx, event in enumerate(events, 1):
        print(f"{idx}. {event['event']} - {event['handler']}")
    return events

def get_event_numbers():
    numbers_input = input("Введите номера событий для удаления через запятую или пробел: ")
    numbers = [int(number.strip()) for number in numbers_input.replace(',', ' ').split()]
    return numbers

def main():
    config_data = utilities.choose_configuration()
    if not config_data:
        return
    events = list_events(config_data)
    if not events:
        return
    
    event_numbers = get_event_numbers()
    for number in event_numbers:
        if number <= len(events) and number > 0:
            event = events[number - 1]
            response = crest.call_api('POST', 
                                    'event.unbind', 
                                    {'event': event['event'],
                                    'handler': event['handler']
                                    }, 
                                    config_data)
            if 'result' in response:
                print(f"Ответ сервера по событию {event['event']}: {response['result']}")
            elif 'error' in response:
                print(f"Ответ сервера по событию {event['event']}: {response['error']}")
        else:
            print(f"Неверный номер события: {number}")

if __name__ == "__main__":
    main()