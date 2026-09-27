"""CORS allowlist tests - browser SPAs must not get wildcard or credential leakage."""

import pytest
from django.test import Client, override_settings

_ALLOWED_ORIGIN = "https://spa.example.com"


@pytest.mark.django_db
def test_cors_allowed_origin_gets_access_control_allow_origin() -> None:
    """Allowlisted Origin receives Access-Control-Allow-Origin echo (no wildcard)."""
    with override_settings(CORS_ALLOWED_ORIGINS=[_ALLOWED_ORIGIN]):
        response = Client().get("/health/", HTTP_ORIGIN=_ALLOWED_ORIGIN)
    assert response.status_code == 200
    assert response["Access-Control-Allow-Origin"] == _ALLOWED_ORIGIN


@pytest.mark.django_db
def test_cors_disallowed_origin_omits_access_control_allow_origin() -> None:
    """Non-allowlisted Origin must not receive CORS headers - deny by default."""
    with override_settings(CORS_ALLOWED_ORIGINS=[_ALLOWED_ORIGIN]):
        response = Client().get("/health/", HTTP_ORIGIN="https://evil.example.com")
    assert response.status_code == 200
    assert "Access-Control-Allow-Origin" not in response
