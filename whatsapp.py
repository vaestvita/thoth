import requests
import base64

import bitrix


def webhook_subscribe(config_data, received_token):
    whatsapp_data = config_data['messengers']['whatsapp']
    
    for entry in whatsapp_data:
        if 'verify_token' in entry and entry['verify_token'] == received_token:
            return True
    return False


def message_route(config_data, phone_number_id):
    whatsapp_data = config_data['messengers']['whatsapp']
    
    # Итерация по списку данных whatsapp
    for entry in whatsapp_data:
        # Проверка наличия и соответствия phone_number_id
        if entry.get('phone_id') == phone_number_id:
            # Возврат значений connector_id и line_id для найденного phone_number_id
            return entry['connector_id'], entry['line_id']
    
    # Возврат None, если phone_number_id не найден
    return None, None


def message_processing(entry, config_data):
    changes = entry['changes'][0]['value']
    if 'contacts' in changes:
        phone_number_id = changes['metadata']['phone_number_id']
        connector_id, line_id = message_route(config_data, phone_number_id)
        connector_data = {
            'connector_id': connector_id,
            'line_id': line_id
        }       
        if connector_id and line_id:
            message_type = changes['messages'][0]['type']

            message_params = {
                'b24_connector': connector_id,
                'b24_line': line_id,
                'phone_number_id' : phone_number_id,
                'name': changes['contacts'][0]['profile']['name'],
                'wa_id': changes['contacts'][0]['wa_id'],
            }

            if message_type == 'text':
                message_params['body'] = changes['messages'][0]['text']['body']

            elif message_type == 'contacts':
                contacts = changes['messages'][0]['contacts']

                message_params['body'] = format_contacts(contacts)

            elif message_type in ['image', 'video', 'audio', 'document']:
                media_data = changes['messages'][0][message_type]
                media_id = media_data['id']
                if 'filename' in media_data:
                    file_name = media_data['filename']
                else:
                    extension = media_data['mime_type'].split('/')[1].split(';')[0]
                    file_name = f'{media_id}.{extension}'
                message_params['body'] = file_name
                if 'caption' in media_data:
                    message_params['body'] = media_data['caption']

                message_params['file_url'] = get_file_data(config_data, media_id, file_name, connector_data)

            else:
                phone = changes['contacts'][0]['wa_id']
                message = {}
                message['type'] = 'text'
                message['text'] = {'body': '( ͡° ͜ʖ ͡°) \nЭтот тип сообщений не принимается.'}
                response = send_message(config_data, [phone], message, connector_data)
                print('RESPONSE', response)
                return response

            return bitrix.send_message(config_data, message_params)
    
    else:
        return 'Success', 200
         

def format_contacts(contacts):
    contact_text = "Присланы контакты:\n"
    for i, contact in enumerate(contacts, start=1):
        name = contact['name']['formatted_name']
        phones = ', '.join([phone['phone'] for phone in contact.get('phones', [])])
        emails = ', '.join([email['email'] for email in contact.get('emails', [])])
        
        contact_info = f"{i}. {name}"
        if phones:
            contact_info += f", {phones}"
        if emails:
            contact_info += f", {emails}"
        
        contact_text += contact_info + "\n"
    
    return contact_text


def send_message(config_data, personal_mobile, message, connector_data):
    try:
        all_whatsapp = config_data['messengers']['whatsapp']
        current_whatsapp = get_whatsapp(all_whatsapp, connector_data['connector_id'], connector_data['line_id'])
        phone_id = current_whatsapp['phone_id']
        access_token = current_whatsapp['access_token']

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }

        for mobile in personal_mobile:
            message_data = {
                'to': mobile,
                'messaging_product': 'whatsapp',
                'recipient_type': 'individual',
                'type': message['type'],
                **message
            }

            response = requests.post(f'https://graph.facebook.com/v19.0/{phone_id}/messages', 
                                    headers=headers, json=message_data)
            return response.status_code, response.json()

    except Exception as e:
        return 500, {'error': str(e)}


def get_whatsapp(whatsapp_data, connector_id, line_id):
    for entry in whatsapp_data:
        if entry.get('connector_id') == connector_id and str(entry.get('line_id')) == str(line_id):
            return {
                'phone_id': entry.get('phone_id'),
                'access_token': entry.get('access_token')
            }
    return None


def get_file_data(config_data, media_id, filename, connector_data):
    all_whatsapp = config_data['messengers']['whatsapp']
    current_whatsapp = get_whatsapp(all_whatsapp, connector_data['connector_id'], connector_data['line_id'])
    access_token = current_whatsapp['access_token']

    headers = {
    'Authorization': f'Bearer {access_token}',
    'Content-Type': 'application/json'
        }
    
    media_data = requests.get(f'https://graph.facebook.com/v19.0/{media_id}', headers=headers).json()

    media_url = media_data['url']
    filename = f"{media_id}_{filename}"    
    return download_file(config_data, media_url, filename, headers)


def download_file(config_data, media_url, filename, headers):
    response = requests.get(media_url, headers=headers)
    if response.status_code == 200:
        file_content_base64 = base64.b64encode(response.content).decode('utf-8')
        response = bitrix.uploadfile(config_data, file_content_base64, filename)

        if 'result' in response:      
            file_url = response['result']['DOWNLOAD_URL']
            return file_url
        else:
            print('error', response)
        