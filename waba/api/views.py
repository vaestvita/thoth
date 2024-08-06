# waba/views.py
from rest_framework.mixins import CreateModelMixin
from rest_framework.viewsets import GenericViewSet
from django.http import HttpResponse
from .serializers import WabaSerializer, PhoneSerializer
from waba.models import Waba, Phone
from waba.utils import message_processing
import logging

logger = logging.getLogger(__name__)

class WabaWebhook(GenericViewSet, CreateModelMixin):
    queryset = Phone.objects.all()
    serializer_class = PhoneSerializer

    def create(self, request, *args, **kwargs):
        if request.method == 'GET':
            hub_mode = request.query_params.get('hub.mode')
            hub_challenge = request.query_params.get('hub.challenge')
            hub_verify_token = request.query_params.get('hub.verify_token')

            if hub_mode == 'subscribe' and hub_verify_token:
                try:
                    waba = Waba.objects.get(verify_token=hub_verify_token)
                    return HttpResponse(hub_challenge, content_type='text/plain')
                except Waba.DoesNotExist:
                    return HttpResponse('Verification token not found', status=400, content_type='text/plain')
            return HttpResponse('Bad Request', status=400, content_type='text/plain')
        
        elif request.method == 'POST':
            logger.info("Received data: %s", request.data)
            return message_processing(request)

    def list(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)