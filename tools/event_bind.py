import utilities
import crest

def get_events_input():
    events_input = input("Введите коды событий через запятую или пробел: ")
    events_list = [event.strip() for event in events_input.replace(',', ' ').split()]
    return events_list

def main():
    config_data = utilities.choose_configuration()
    if not config_data:
        return

    events_to_bind = get_events_input()
    if not events_to_bind:
        return

    get_events_response = crest.call_api('GET', 'event.get', {}, config_data)
    registered_events = {}
    if 'result' in get_events_response:
        registered_events = {event['event'].upper(): event['handler'] for event in get_events_response['result']}

    placement_handler = config_data['bitrix']['handler']
    for event in events_to_bind:
        event_upper = event.upper()
        
        if event_upper in registered_events:
            if registered_events[event_upper] == placement_handler:
                print(f"Событие {event} уже зарегистрировано с handler {placement_handler}.")
                continue
            else:
                print(f"Обновление handler для события {event}.")

        response = crest.call_api('POST', 'event.bind', {'event': event, 'handler': placement_handler}, config_data)
        
        if 'error' in response:
            print(f"Ошибка при привязке события {event}: {response['error_description']}")
        else:
            print(f"Событие {event} успешно привязано к handler {placement_handler}.")

if __name__ == "__main__":
    main()