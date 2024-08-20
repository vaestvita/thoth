from rest_framework import serializers

from thoth.bitrix.models import Bitrix


class PortalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bitrix
        fields = [
            "owner",
            "user_id",
            "domain",
            "client_endpoint",
        ]

    def create(self, validated_data):
        return Bitrix.objects.create(**validated_data)
