import os
import base64
import requests
import time
import configparser

from panoramisk import Manager, Message

import bitrix

config = configparser.ConfigParser()
config.read('config.ini')

# данные для доступа к AMI
HOST = config.get('asterisk', 'host')
PORT = config.get('asterisk', 'port')
USER = config.get('asterisk', 'username')
SECRET = config.get('asterisk', 'secret')
RECORDS_URL = config.get('asterisk', 'records_url')

def to_list(input_string):
    return [item.strip() for item in input_string.split(',')]

INBOUND_CONTEXTS = to_list(config.get('asterisk', 'inbound_contexts'))
HANGUP_DELISTING = to_list(config.get('asterisk', 'hangup_delisting'))

calls_data = {}

dial_status = {
    '3': 503,
    '17': 486,
    '19': 304,
    '20': 480,
    '21': 304,
    '31': 200,
    '34': 404,
    '38': 503,
    '127': 603
}


manager = Manager(
    host=os.getenv('AMI_HOST', HOST),
    port=os.getenv('AMI_PORT', PORT),
    username=os.getenv('AMI_USERNAME', USER),
    secret=os.getenv('AMI_SECRET', SECRET),
    ping_delay=10,  # Delay after start
    ping_interval=10,  # Periodically ping AMI (dead or alive)
    reconnect_timeout=0.1,  # Timeout reconnect if connection lost
)

# Событие ClickToCall
async def initiate_call(extension, phone_num, bitrix_id, bitrix_user):

    action = {
        'Action': 'Originate',
        'Channel': f'Local/{extension}@from-internal',
        'Variable': f'BITRIX_ID={bitrix_id},BITRIX_USER={bitrix_user}',
        'WaitTime': 20,
        'CallerID': phone_num,
        'Exten': phone_num,
        'Context': 'from-internal',
        'Priority': 1
    }

    await manager.send_action(action)


@manager.register_event('*')  # Register all events
async def ami_callback(mngr: Manager, message: Message):
    call_id = message.Linkedid
    default_user = False
    
    # Событие ClickToCall
    if message.Variable == 'BITRIX_ID':
        calls_data[call_id] = {'start_time': time.time()}
        calls_data[call_id]['bitrix_call_id'] = message.Value
        calls_data[call_id]['click_to_call'] = True
    elif message.Variable == 'BITRIX_USER':
        calls_data[call_id]['bitrix_user_id'] = message.Value
    
    # Новый звонок
    if message.Event == 'Newchannel':
        if call_id not in calls_data:
            calls_data[call_id] = {'start_time': time.time()}

        # Входящий звонок
        if message.Context in INBOUND_CONTEXTS:
            if message.CallerIDNum != '<unknown>':
                calls_data[call_id]['phone_number'] = message.CallerIDNum
                calls_data[call_id]['internall_call'] = False
        
        # Если звонок в группу, ставим метку
        elif message.Context == 'from-queue':
            calls_data[call_id]['from_queue'] = True      

        # Регистрация входящего звонка и карточка
        elif message.Context == 'from-internal':
            if 'bitrix_user_id' not in calls_data[call_id]:
                bitrix_user_id, default_user = bitrix.get_user_info(user_phone=message.CallerIDNum)
                calls_data[call_id]['bitrix_user_id'] = bitrix_user_id
            if message.Exten == 's':
                # Для первого в очереди или единственного вн номера
                if 'bitrix_call_id' not in calls_data[call_id]:
                    phone_number = calls_data[call_id].get('phone_number')
                    if phone_number:
                        calls_data[call_id]['bitrix_call_id'] = bitrix.register_call(bitrix_user_id, phone_number, 2)

                # Для последующих в очереди или группе показываем карточку
                elif not default_user and not calls_data[call_id].get('internall_call'):
                    bitrix.card_action(calls_data[call_id].get('bitrix_call_id'), calls_data[call_id]['bitrix_user_id'], 'show')

            # Исходящий звонок - регистрация
            else:
                if len(message.Exten) < 5:
                    calls_data[call_id]['internall_call'] = True
                    return
                calls_data[call_id]['bitrix_call_id'] = bitrix.register_call(bitrix_user_id, message.Exten, 1)
    
    # Получение пути файла записи разговора
    elif message.Variable == 'MIXMONITOR_FILENAME':
        if 'file_patch' not in calls_data[call_id]:
            calls_data[call_id]['file_patch'] = message.Value.split("monitor/")[1]
            calls_data[call_id]['file_name'] = os.path.basename(message.Value)

    # Перехват звонка
    elif message.Event == 'Pickup':
        call_id = message.TargetLinkedid
        bitrix.card_action(calls_data[call_id]['bitrix_call_id'], calls_data[call_id].get('bitrix_user_id'), 'hide')
        calls_data[call_id]['bitrix_user_id'], _ = bitrix.get_user_info(user_phone=message.CallerIDNum)
        calls_data[call_id]['call_status'] = 200
    
    # Ответ на звонок
    elif message.Event == 'BridgeEnter':
        if message.Priority != '1' or message.Linkedid not in calls_data:
            return
        if message.Context == 'from-internal' and not calls_data[call_id].get('click_to_call'):
            pass
        # Для исходящих и входящих установка статуса
        elif message.Context in INBOUND_CONTEXTS:
            pass
        elif message.Context in ['macro-dial-one']:
            calls_data[call_id]['bitrix_user_id'], _ = bitrix.get_user_info(user_phone=message.CallerIDNum)
        else:
            return

        calls_data[call_id]['call_status'] = 200

    # Трансфер звонка
    elif message.Event == 'BlindTransfer' and message.Result == 'Success':
        call_id = message.TransfererLinkedid
        bitrix.card_action(calls_data[call_id]['bitrix_call_id'], calls_data[call_id].get('bitrix_user_id'), 'hide')
        calls_data[call_id]['bitrix_user_id'], _ = bitrix.get_user_info(user_phone=message.Extension)
    
    # Завершение звонка
    elif message.Event == 'Hangup':
        if call_id not in calls_data:
            return
        call_data = calls_data.get(call_id)
        if message.Context == 'from-internal' and message.ChannelState in ['5']:

            # Если перезагрузка звонка в очереди или ответил кто-то, закрываем карточку
            bitrix_user_id, default_user = bitrix.get_user_info(user_phone=message.CallerIDNum)
            if not default_user:
                bitrix.card_action(call_data.get('bitrix_call_id'), bitrix_user_id, 'hide')

        elif message.Context not in HANGUP_DELISTING:
            # Если стоит метка from_queue значит звонок был в очереди
            if call_data.get('from_queue') and message.Context == 'ext-local':
                return
            
           # Установка статуса звонка, если он еще не установлен
            if 'call_status' not in call_data:
                call_data["call_status"] = dial_status.get(message.Cause, 304)

            # Добавление пользователя по умолчанию если вызов сброшен до регистрации
            if 'bitrix_user_id' not in call_data:
                bitrix_user_id, _ = bitrix.get_user_info(user_phone=None)
                call_data['bitrix_user_id'] = bitrix_user_id
                call_data['bitrix_call_id'] = bitrix.register_call(bitrix_user_id, call_data.get('phone_number'), 2)

            # Закрытие звонка в битрикс
            if bitrix.finish_call(call_data) and call_data["call_status"] == 200 and 'file_patch' in call_data:

                # передача записи звонка
                file_url = f'{RECORDS_URL}{call_data["file_patch"]}'
                response = requests.get(file_url)
                if response.status_code == 200:
                    encoded_file = base64.b64encode(response.content)

                    bitrix.attachRecord(call_data, encoded_file)
            else:
                del calls_data[call_id]

            print(calls_data)
            if call_id in calls_data:
                del calls_data[call_id]


if __name__ == '__main__':
    manager.connect(run_forever=True)