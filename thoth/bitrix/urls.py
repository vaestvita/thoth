from django.urls import path

from .api.views import PlacementOptionsViewSet
from .api.views import SmsViewSet
from .views import portals, faq_view

urlpatterns = [
    path(
        "api/bitrix/placement/",
        PlacementOptionsViewSet.as_view({"post": "create"}),
        name="placement",
    ),
    path("api/bitrix/sms/", SmsViewSet.as_view({"post": "create"}), name="sms"),
    # path('api/bitrix/olx/', )
    path("portals/", portals, name="portals"),
    path('faq/', faq_view, name='faq'),
    # other paths...
]
