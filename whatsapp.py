import requests
import re
import base64

import crest, bitrix


def webhook_subscribe(config_value, received_token):
    whatsapp_data = crest.get_params(config_value, 'whatsapp')
    if received_token == whatsapp_data['verify_token']:
        return True
    else:
        return False
    

def message_processing(entry, config_value):

    changes = entry['changes'][0]['value']
    if 'contacts' in changes:
        message_type = changes['messages'][0]['type']

        message_params = {
            'phone_number_id' : changes['metadata']['phone_number_id'],
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
            message_params['file_url'] = get_file_data(config_value, media_id, file_name)

        else:
            phone = changes['contacts'][0]['wa_id']
            message = '( ͡° ͜ʖ ͡°) \nЭтот тип сообщений не принимается.'           
            return send_message(config_value, phone, message)

        return bitrix.send_message(config_value, message_params)
    
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


def send_message(config_value, phone, message):
    try:
        whatsapp_data = crest.get_params(config_value, 'whatsapp')        
        phone_number_id = whatsapp_data['phone_number_id']
        access_token = whatsapp_data['access_token']

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }

        message_data = {
            'to': phone,
            'messaging_product': 'whatsapp',
            'recipient_type': 'individual',
            'type': message['type'],
            **message
        }

        response = requests.post(f'https://graph.facebook.com/v19.0/{phone_number_id}/messages', 
                                 headers=headers, json=message_data)
        return response.status_code, response.json()

    except Exception as e:
        return 500, {'error': str(e)}
    

def get_file_data(config_value, media_id, filename):
    whatsapp_data = crest.get_params(config_value, 'whatsapp')
    access_token = whatsapp_data['access_token']

    headers = {
    'Authorization': f'Bearer {access_token}',
    'Content-Type': 'application/json'
        }
    
    media_data = requests.get(f'https://graph.facebook.com/v19.0/{media_id}', headers=headers).json()

    media_url = media_data['url']
    filename = f"{media_id}_{filename}"    
    return download_file(config_value, media_url, filename, headers)


def download_file(config_value, media_url, filename, headers):
    response = requests.get(media_url, headers=headers)
    if response.status_code == 200:
        file_content_base64 = base64.b64encode(response.content).decode('utf-8')
        response = bitrix.uploadfile(config_value, file_content_base64, filename)
        
        file_url = response['result']['DOWNLOAD_URL']

        return file_url
        