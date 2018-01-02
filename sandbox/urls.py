from django.conf.urls import include, url
from django.contrib import admin
from oscar.app import application
from oscarapi.app import application as api
from oscarapicheckout.app import application as oscar_api_checkout
from cybersource.app import application as cybersource

urlpatterns = [
    url(r'^i18n/', include('django.conf.urls.i18n')),
    url(r'^admin/', admin.site.urls),

    url(r'^api/cybersource/', cybersource.urls),
    url(r'^api/', oscar_api_checkout.urls),
    url(r'^api/', api.urls),

    url(r'', application.urls),
]
