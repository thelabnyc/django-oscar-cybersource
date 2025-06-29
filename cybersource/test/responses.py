from pathlib import Path
from typing import TYPE_CHECKING
import re

from ..conf import settings

if TYPE_CHECKING:
    from requests_mock.mocker import Mocker

_base = Path(__file__).resolve().parent / "responses/"

SOAP_AFS_ACCEPT = (_base / "soap-afs-accept.xml").read_text()
SOAP_AFS_REVIEW = (_base / "soap-afs-review.xml").read_text()
SOAP_AFS_REJECT = (_base / "soap-afs-reject.xml").read_text()

SOAP_AUTH_ACCEPT = (_base / "soap-auth-accept.xml").read_text()
SOAP_AUTH_REVIEW = (_base / "soap-auth-review.xml").read_text()
SOAP_AUTH_REJECT = (_base / "soap-auth-reject.xml").read_text()

SOAP_CAPTURE = (_base / "soap-capture.xml").read_text()


def mock_soap_transaction_response(rmock: "Mocker", resp_xml: str) -> None:
    # Allow GETs to the WSDL / XSD files to pass through
    wsdl = settings.WSDL
    match_cyb_host = re.compile(rf"^{wsdl.scheme}:\/\/{wsdl.host}")
    rmock.register_uri("GET", match_cyb_host, real_http=True)
    # Intercept POSTs and mock the response
    rmock.register_uri("POST", match_cyb_host, text=resp_xml)
