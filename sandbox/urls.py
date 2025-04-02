from django.apps import apps
from django.contrib import admin
from django.urls import include, path

cybersource = apps.get_app_config("cybersource")
oscarapicheckout = apps.get_app_config("oscarapicheckout")
oscar = apps.get_app_config("oscar")

urlpatterns = [
    path("i18n/", include("django.conf.urls.i18n")),
    path("admin/", admin.site.urls),
    path(
        "api/cybersource/",
        include(
            cybersource.urls[0]  # type:ignore[attr-defined]
        ),
    ),
    path(
        "api/",
        include(
            oscarapicheckout.urls[0]  # type:ignore[attr-defined]
        ),
    ),
    path("api/", include("oscarapi.urls")),
    path(
        "",
        include(
            oscar.urls[0]  # type:ignore[attr-defined]
        ),
    ),
]
