from rest_framework import serializers

from thoth.bitrix.models import Bitrix


class PortalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bitrix
        fields = [
            "owner",
            "domain",
            "client_endpoint",
            "access_token",
            "refresh_token",
            "application_token",
        ]

    def create(self, validated_data):
        return Bitrix.objects.create(**validated_data)
