"""GET /api/v1/me - SPA caller identity from the validated token only."""

import pytest
from core.auth.testing import mint_test_token
from django.urls import reverse
from rest_framework.test import APIClient


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


def test_me_valid_token_returns_sub_and_role(api_client: APIClient) -> None:
    """Authenticated caller sees their own sub/role - no DB lookup."""
    sub = "00000000-0000-4000-8000-000000000099"
    token = mint_test_token(sub=sub, role="admin")
    response = api_client.get(
        reverse("me"),
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert response.status_code == 200
    assert response.json() == {"sub": sub, "role": "admin"}


def test_me_missing_token_returns_401(api_client: APIClient) -> None:
    """Unauthenticated requests are rejected - deny by default."""
    response = api_client.get(reverse("me"))
    assert response.status_code == 401


def test_me_invalid_token_returns_401(api_client: APIClient) -> None:
    """Bad bearer tokens must not yield caller identity."""
    response = api_client.get(
        reverse("me"),
        HTTP_AUTHORIZATION="Bearer not-a-valid-jwt",
    )
    assert response.status_code == 401
