from django.test import TestCase
from django.urls import reverse

from ..conf import settings


class FingerprintRedirectViewTest(TestCase):
    def test_img1(self):
        session = self.client.session
        session["cybersource_fingerprint_session_id"] = "foo"
        session.save()
        url = reverse("cybersource-fingerprint-redirect", args=["img-1"])
        expected = (
            "https://h.online-metrix.net/fp/clear.png?org_id=%s&session_id=%s%s&m=1"
            % (settings.ORG_ID, settings.MERCHANT_ID, "foo")
        )

        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, expected)

    def test_img2(self):
        session = self.client.session
        session["cybersource_fingerprint_session_id"] = "bar"
        session.save()
        url = reverse("cybersource-fingerprint-redirect", args=["img-2"])
        expected = (
            "https://h.online-metrix.net/fp/clear.png?org_id=%s&session_id=%s%s&m=2"
            % (settings.ORG_ID, settings.MERCHANT_ID, "bar")
        )

        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, expected)

    def test_flash(self):
        session = self.client.session
        session["cybersource_fingerprint_session_id"] = "baz"
        session.save()
        url = reverse("cybersource-fingerprint-redirect", args=["flash"])
        expected = (
            "https://h.online-metrix.net/fp/fp.swf?org_id={}&session_id={}{}".format(
                settings.ORG_ID,
                settings.MERCHANT_ID,
                "baz",
            )
        )

        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, expected)

    def test_js(self):
        session = self.client.session
        session["cybersource_fingerprint_session_id"] = "bat"
        session.save()
        url = reverse("cybersource-fingerprint-redirect", args=["js"])
        expected = (
            "https://h.online-metrix.net/fp/check.js?org_id=%s&session_id=%s%s"
            % (settings.ORG_ID, settings.MERCHANT_ID, "bat")
        )

        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, expected)

    def test_unknown(self):
        url = reverse("cybersource-fingerprint-redirect", args=["something"])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
