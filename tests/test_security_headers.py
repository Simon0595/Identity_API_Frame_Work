"""Security response headers on API responses."""

import pytest
from django.test import Client


@pytest.mark.django_db
def test_security_headers_present_on_health_response() -> None:
    """JSON endpoints expose explicit CSP, Permissions-Policy, and Referrer-Policy."""
    response = Client().get("/health/")
    assert response.status_code == 200
    assert response["Content-Security-Policy"] == "default-src 'none'"
    assert "geolocation=()" in response["Permissions-Policy"]
    assert response["Referrer-Policy"] == "same-origin"
