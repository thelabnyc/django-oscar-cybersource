from django.conf.urls import url
from django.views.decorators.csrf import csrf_exempt
from oscar.core.application import Application
from .views import CyberSourceReplyView, FingerprintRedirectView, DecisionManagerNotificationView


class CybersourceApplication(Application):
    def get_urls(self):
        cs_reply = csrf_exempt(CyberSourceReplyView.as_view())
        review_notification = csrf_exempt(DecisionManagerNotificationView.as_view())
        fingerprint = FingerprintRedirectView.as_view()

        urlpatterns = [
            url(r'^cybersource-reply/$', cs_reply, name='cybersource-reply'),
            url(r'^decision-manager-review-notification/$', review_notification, name='cybersource-review-notification'),
            url(r'^fingerprint/(?P<url_type>.*)/$', fingerprint, name='cybersource-fingerprint-redirect'),
        ]
        return self.post_process_urls(urlpatterns)


application = CybersourceApplication()
