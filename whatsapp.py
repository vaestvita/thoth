import requests
import re

import crest


def webhook_subscribe(config_value, received_token):
    whatsapp_data = crest.get_params(config_value, 'whatsapp')
    if received_token == whatsapp_data['verify_token']:
        return True
    else:
        return False    


def send_message(config_value, phone, message):
    try:
        whatsapp_data = crest.get_params(config_value, 'whatsapp')        
        phone_number_id = whatsapp_data['phone_number_id']
        access_token = whatsapp_data['access_token']

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }

        text = re.sub(r'\[(?!(br|\n))[^\]]+\]', '', message)
        text = text.replace('[br]', '\n')

        message_data = {
            'messaging_product': 'whatsapp',
            'to': phone,
            'type': 'text',
            'recipient_type': 'individual',
            'text': {
                'preview_url': 'false',
                'body': text
            }
        }

        response = requests.post(f'https://graph.facebook.com/v17.0/{phone_number_id}/messages', 
                                 headers=headers, json=message_data).json()

        return response
    
    except Exception as e:
        return {'error': str(e)}
        