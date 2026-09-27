"""Global anon and authenticated read throttles - OWASP API4."""

import uuid

import pytest
from core.auth.testing import mint_test_token
from django.core.cache import cache
from django.core.management import call_command
from django.urls import reverse
from domain.management.commands.seed import SEED_PERSON_ID
from domain.models import Context, Role
from domain.throttling import GlobalAnonRateThrottle, IdentityReadThrottle
from rest_framework.test import APIClient


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def seeded_person_id(db: None) -> uuid.UUID:
    call_command("seed")
    return SEED_PERSON_ID


def test_anon_throttle_returns_429_when_rate_exceeded(api_client: APIClient) -> None:
    """Unauthenticated traffic is IP-keyed; exceed public-endpoint quota: 429."""
    original_rates = GlobalAnonRateThrottle.THROTTLE_RATES
    try:
        GlobalAnonRateThrottle.THROTTLE_RATES = {"anon": "1/min"}
        cache.clear()

        url = reverse("health")
        first = api_client.get(url)
        assert first.status_code == 200

        second = api_client.get(url)
        assert second.status_code == 429
    finally:
        GlobalAnonRateThrottle.THROTTLE_RATES = original_rates


@pytest.mark.django_db
def test_authenticated_read_throttle_returns_429_when_rate_exceeded(
    api_client: APIClient,
    seeded_person_id: uuid.UUID,
) -> None:
    """Authenticated reads are per-sub - exceed quota after a successful read -> 429."""
    original_rates = IdentityReadThrottle.THROTTLE_RATES
    try:
        IdentityReadThrottle.THROTTLE_RATES = {"identity_read": "1/min"}
        cache.clear()

        token = mint_test_token(role=Role.COLLEAGUE)
        url = reverse("identity-read", kwargs={"person_id": seeded_person_id})

        first = api_client.get(
            url,
            {"context": Context.PROFESSIONAL},
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        assert first.status_code == 200

        second = api_client.get(
            url,
            {"context": Context.PROFESSIONAL},
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        assert second.status_code == 429
    finally:
        IdentityReadThrottle.THROTTLE_RATES = original_rates
