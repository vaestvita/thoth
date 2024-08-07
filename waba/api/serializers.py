from rest_framework import serializers
from waba.models import Waba, Phone

class WabaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Waba
        fields = ['verify_token', 'access_token', 'owner', 'bitrix']

class PhoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Phone
        fields = ['phone', 'phone_id', 'sms_service', 'waba', 'owner', 'line']
