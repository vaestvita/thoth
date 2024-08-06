import os
import base64

from thoth.settings import env

from .crest import call_method

HOME_URL = env('HOME_URL')
EVENTS = ['ONIMCONNECTORMESSAGEADD', 'ONIMCONNECTORLINEDELETE', 'ONIMCONNECTORSTATUSDELETE']

dir = os.path.dirname(os.path.abspath(__file__))
waba_logo = os.path.join(dir, 'img', 'WhatsApp.svg')

with open(waba_logo, 'rb') as file:
    image_data = file.read()

encoded_image = f"data:image/svg+xml;base64,{base64.b64encode(image_data).decode('utf-8')}"

# Регистрация коннектора
def register_connector(domain, api_key):

    payload = {
        'ID': 'thoth_waba',
        'NAME': 'THOTH WABA',
        'ICON': {
            'DATA_IMAGE': encoded_image
        },
        'PLACEMENT_HANDLER': HOME_URL
    }

    call_method(domain, 'POST', 'imconnector.register', payload)

    # Подписка на события
    for event in EVENTS:

        payload = {
            'event': event,
            'HANDLER': f'{HOME_URL}/api/bitrix/?api-key={api_key}'
        }

        call_method(domain, 'POST', 'event.bind', payload)