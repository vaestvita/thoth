from rest_framework.mixins import ListModelMixin, CreateModelMixin
from rest_framework.viewsets import GenericViewSet

from bitrix.models import Bitrix
from .serializers import PortalSerializer

from bitrix.utils import event_processor


class PortalViewSet(CreateModelMixin, GenericViewSet, ListModelMixin):
    queryset = Bitrix.objects.all()
    serializer_class = PortalSerializer

    def create(self, request, *args, **kwargs):

        return event_processor(self, request)