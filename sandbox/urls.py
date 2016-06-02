from django.conf.urls import patterns, include, url
from django.contrib import admin
from oscar.app import application
from oscarapi.app import application as api
from oscarapicheckout.app import application as oscar_api_checkout
from cybersource.app import application as cybersource

urlpatterns = patterns('',
    url(r'^i18n/', include('django.conf.urls.i18n')),
    url(r'^admin/', include(admin.site.urls)),

    url(r'^api/cybersource/', include(cybersource.urls)),
    url(r'^api/', include(oscar_api_checkout.urls)),
    url(r'^api/', include(api.urls)),

    url(r'', include(application.urls)),
)
