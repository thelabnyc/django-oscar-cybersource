from django.apps import apps
from django.conf.urls import include
from django.contrib import admin
from django.urls import path

urlpatterns = [
    path("i18n/", include("django.conf.urls.i18n")),
    path("admin/", admin.site.urls),
    path("api/cybersource/", include(apps.get_app_config("cybersource").urls[0])),
    path("api/", include(apps.get_app_config("oscarapicheckout").urls[0])),
    path("api/", include("oscarapi.urls")),
    path("", include(apps.get_app_config("oscar").urls[0])),
]
