from __future__ import annotations

from typing import TYPE_CHECKING, List

from django.urls import path
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import csrf_exempt
from oscar.core.application import OscarConfig

if TYPE_CHECKING:
    from django.urls.resolvers import URLPattern


class CybersourceConfig(OscarConfig):
    name = "cybersource"
    label = "cybersource"
    verbose_name = _("Oscar API-Checkout Cybersource Payment Adapter")
    namespace = "cybersource"
    default = True

    def get_urls(self) -> List[URLPattern]:
        from .views import (
            CyberSourceReplyView,
            DecisionManagerNotificationView,
            FingerprintRedirectView,
        )

        cs_reply = csrf_exempt(CyberSourceReplyView.as_view())
        review_notification = csrf_exempt(DecisionManagerNotificationView.as_view())
        fingerprint = FingerprintRedirectView.as_view()

        urlpatterns = [
            path("cybersource-reply/", cs_reply, name="cybersource-reply"),
            path(
                "decision-manager-review-notification/",
                review_notification,
                name="cybersource-review-notification",
            ),
            path(
                "fingerprint/<str:url_type>/",
                fingerprint,
                name="cybersource-fingerprint-redirect",
            ),
        ]
        return self.post_process_urls(urlpatterns)
