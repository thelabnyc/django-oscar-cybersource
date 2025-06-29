from django.http import HttpRequest
from rest_framework.authentication import SessionAuthentication


class CSRFExemptSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request: HttpRequest) -> None:
        return
