from django.conf import settings
from rest_framework.routers import DefaultRouter
from rest_framework.routers import SimpleRouter

from thoth.bitrix.api.views import PortalViewSet
from thoth.users.api.views import UserViewSet
from thoth.waba.api.views import WabaWebhook

router = DefaultRouter() if settings.DEBUG else SimpleRouter()

router.register("users", UserViewSet)
router.register("bitrix", PortalViewSet)
router.register("waba", WabaWebhook)


app_name = "api"
urlpatterns = router.urls
