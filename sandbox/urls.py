from django.apps import apps
from django.conf.urls import include
from django.urls import re_path
from django.contrib import admin


urlpatterns = [
    re_path(r"^i18n/", include("django.conf.urls.i18n")),
    re_path(r"^admin/", admin.site.urls),
    re_path(r"^api/cybersource/", include(apps.get_app_config("cybersource").urls[0])),
    re_path(r"^api/", include(apps.get_app_config("oscarapicheckout").urls[0])),
    re_path(r"^api/", include("oscarapi.urls")),
    re_path(r"", include(apps.get_app_config("oscar").urls[0])),
]
