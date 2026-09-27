"""POST /api/v1/dev/login - offline token minting trust boundary."""

import pytest
from core.auth.verifier import get_token_verifier
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APIClient


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@override_settings(AUTH_ISSUER="local", DEBUG=True)
def test_dev_login_local_debug_mints_usable_token(api_client: APIClient) -> None:
    """Offline demo path: local issuer + DEBUG mints a token /me accepts."""
    response = api_client.post(
        reverse("dev-login"),
        {"role": "admin"},
        format="json",
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "Bearer"
    assert "access_token" in body

    claims = get_token_verifier().verify(body["access_token"])
    assert claims["role"] == "admin"
    assert claims["sub"] == "00000000-0000-4000-8000-000000000001"

    me = api_client.get(
        reverse("me"),
        HTTP_AUTHORIZATION=f"Bearer {body['access_token']}",
    )
    assert me.status_code == 200
    assert me.json() == {"sub": claims["sub"], "role": "admin"}


@override_settings(AUTH_ISSUER="local", DEBUG=False)
def test_dev_login_refused_when_debug_off(api_client: APIClient) -> None:
    """DEBUG=False hides dev login even with local issuer - fail closed."""
    response = api_client.post(
        reverse("dev-login"),
        {"role": "colleague"},
        format="json",
    )
    assert response.status_code == 404


@override_settings(AUTH_ISSUER="cognito", DEBUG=True)
def test_dev_login_refused_when_issuer_not_local(api_client: APIClient) -> None:
    """Cognito/non-local issuer must not expose offline token minting."""
    response = api_client.post(
        reverse("dev-login"),
        {"role": "colleague"},
        format="json",
    )
    assert response.status_code == 404


@override_settings(AUTH_ISSUER="local", DEBUG=True)
def test_dev_login_rejects_unexpected_fields(api_client: APIClient) -> None:
    """Mass-assignment guard - only role/sub are writable."""
    response = api_client.post(
        reverse("dev-login"),
        {"role": "colleague", "is_superuser": True},
        format="json",
    )
    assert response.status_code == 400
