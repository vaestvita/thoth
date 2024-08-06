"""
URL configuration for thoth project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework.authtoken.views import obtain_auth_token
from drf_spectacular.views import SpectacularAPIView
from drf_spectacular.views import SpectacularSwaggerView

from views import home_view
from thoth.settings import env

ADMIN_URL=env('ADMIN_URL', default='admin/')
PORTAL_NAME = 'THOTH'

urlpatterns = [
    path(ADMIN_URL, admin.site.urls),
    path('', home_view, name='home'),
]

# API URLS 
urlpatterns += [
    # API base url
    path("api/", include("thoth.api_router")),
    # DRF auth token
    # path("api/auth-token/", obtain_auth_token),
    path("api/schema/", SpectacularAPIView.as_view(), name="api-schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="api-schema"),
        name="api-docs",
    ),

]


admin.site.site_header = PORTAL_NAME
admin.site.site_title = PORTAL_NAME
admin.site.index_title = PORTAL_NAME