from django.conf.urls import url
from django.views.decorators.csrf import csrf_exempt
from django.utils.translation import gettext_lazy as _
from oscar.core.application import OscarConfig


class CybersourceConfig(OscarConfig):
    name = 'cybersource'
    label = 'cybersource'
    verbose_name = _('Oscar API-Checkout Cybersource Payment Adapter')
    namespace = 'cybersource'


    def get_urls(self):
        from .views import (
            CyberSourceReplyView,
            FingerprintRedirectView,
            DecisionManagerNotificationView,
        )
        cs_reply = csrf_exempt(CyberSourceReplyView.as_view())
        review_notification = csrf_exempt(DecisionManagerNotificationView.as_view())
        fingerprint = FingerprintRedirectView.as_view()

        urlpatterns = [
            url(r'^cybersource-reply/$', cs_reply, name='cybersource-reply'),
            url(r'^decision-manager-review-notification/$', review_notification, name='cybersource-review-notification'),
            url(r'^fingerprint/(?P<url_type>.*)/$', fingerprint, name='cybersource-fingerprint-redirect'),
        ]
        return self.post_process_urls(urlpatterns)
