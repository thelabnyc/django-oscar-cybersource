from django.conf.urls import patterns, url
from django.views.decorators.csrf import csrf_exempt
from rest_framework.urlpatterns import format_suffix_patterns
from .views import (
    CyberSourceReplyView,
    FingerprintRedirectView,
    SignAuthorizePaymentFormView
)


urlpatterns = patterns('',
    url(r'^cybersource-reply/$', csrf_exempt(CyberSourceReplyView.as_view()), name='cybersource-reply'),
    url(r'^fingerprint/(?P<url_type>.*)/$', FingerprintRedirectView.as_view(), name='cybersource-fingerprint-redirect'),
    url(r'^sign-auth-request/$', SignAuthorizePaymentFormView.as_view(), name='cybersource-sign-auth-request'),
)

urlpatterns = format_suffix_patterns(urlpatterns)
