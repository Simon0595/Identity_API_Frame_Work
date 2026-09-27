"""Write path + audit tests - policy, 403 rule, mass-assignment."""

import uuid
from typing import Any

import pytest
from core.auth.testing import mint_test_token
from django.core.cache import cache
from django.core.management import call_command
from django.urls import reverse
from domain.management.commands.seed import DEFAULT_SEED_OWNER_SUB, SEED_PERSON_ID
from domain.models import Action, AuditEntry, Context, ProfileField, Role
from domain.throttling import IdentityWriteThrottle
from rest_framework.test import APIClient


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def seeded_person_id(db: None) -> uuid.UUID:
    call_command("seed")
    return SEED_PERSON_ID


def _auth_get_audit(
    client: APIClient,
    person_id: uuid.UUID,
    *,
    role: str,
) -> Any:
    token = mint_test_token(role=role)
    url = reverse("identity-audit", kwargs={"person_id": person_id})
    return client.get(url, HTTP_AUTHORIZATION=f"Bearer {token}")


def _auth_put(
    client: APIClient,
    person_id: uuid.UUID,
    *,
    role: str,
    context: str,
    body: dict[str, Any],
) -> Any:
    token = mint_test_token(role=role)
    url = reverse(
        "identity-write",
        kwargs={"person_id": person_id, "context": context},
    )
    return client.put(
        url,
        body,
        format="json",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )


@pytest.mark.django_db
def test_authorised_write_persists_only_writable_fields_and_is_audited(
    api_client: APIClient,
    seeded_person_id: uuid.UUID,
) -> None:
    """Subject may update all writable professional fields; action=write is audited."""
    response = _auth_put(
        api_client,
        seeded_person_id,
        role=Role.SUBJECT,
        context=Context.PROFESSIONAL,
        body={
            "fields": {
                "given_name": "Updated Jordan",
                "staff_id": "EMP-99",
            }
        },
    )
    assert response.status_code == 200
    assert response.json()["fields"] == {
        "given_name": "Updated Jordan",
        "staff_id": "EMP-99",
    }

    given_name = ProfileField.objects.get(
        person_id=seeded_person_id,
        context=Context.PROFESSIONAL,
        key="given_name",
    )
    staff_id = ProfileField.objects.get(
        person_id=seeded_person_id,
        context=Context.PROFESSIONAL,
        key="staff_id",
    )
    assert given_name.value == "Updated Jordan"
    assert staff_id.value == "EMP-99"

    entry = AuditEntry.objects.latest("timestamp")
    assert entry.action == Action.WRITE
    assert entry.decision_reason == "policy_allowed"
    assert set(entry.fields_disclosed) == {"given_name", "staff_id"}
    assert "Updated Jordan" not in entry.decision_reason
    assert "EMP-99" not in "".join(entry.fields_disclosed)


@pytest.mark.django_db
def test_unauthorised_write_returns_403_and_writes_nothing(
    api_client: APIClient,
    seeded_person_id: uuid.UUID,
) -> None:
    """Colleague writable set is public-only - restricted staff_id must not persist."""
    before = ProfileField.objects.get(
        person_id=seeded_person_id,
        context=Context.PROFESSIONAL,
        key="staff_id",
    ).value

    response = _auth_put(
        api_client,
        seeded_person_id,
        role=Role.COLLEAGUE,
        context=Context.PROFESSIONAL,
        body={"fields": {"staff_id": "HACKED"}},
    )
    assert response.status_code == 403

    after = ProfileField.objects.get(
        person_id=seeded_person_id,
        context=Context.PROFESSIONAL,
        key="staff_id",
    ).value
    assert after == before

    entry = AuditEntry.objects.latest("timestamp")
    assert entry.action == Action.DENIED
    assert entry.decision_reason == "forbidden_fields"
    assert "staff_id" in entry.fields_disclosed
    assert "HACKED" not in entry.decision_reason


@pytest.mark.django_db
def test_mass_assignment_forbidden_field_rejected(
    api_client: APIClient,
    seeded_person_id: uuid.UUID,
) -> None:
    """Unexpected nested key is rejected - no ORM write, denied audit row."""
    response = _auth_put(
        api_client,
        seeded_person_id,
        role=Role.SUBJECT,
        context=Context.PROFESSIONAL,
        body={"fields": {"given_name": "OK", "is_admin": "true"}},
    )
    assert response.status_code == 403

    given_name = ProfileField.objects.get(
        person_id=seeded_person_id,
        context=Context.PROFESSIONAL,
        key="given_name",
    )
    assert given_name.value == "Jordan"

    entry = AuditEntry.objects.latest("timestamp")
    assert entry.action == Action.DENIED
    assert entry.decision_reason == "forbidden_fields"
    assert "is_admin" in entry.fields_disclosed


@pytest.mark.django_db
def test_mass_assignment_unexpected_top_level_field_rejected(
    api_client: APIClient,
    seeded_person_id: uuid.UUID,
) -> None:
    """Top-level keys other than fields are rejected before any DB write."""
    response = _auth_put(
        api_client,
        seeded_person_id,
        role=Role.SUBJECT,
        context=Context.PROFESSIONAL,
        body={"fields": {"given_name": "OK"}, "role": "admin"},
    )
    assert response.status_code == 403

    given_name = ProfileField.objects.get(
        person_id=seeded_person_id,
        context=Context.PROFESSIONAL,
        key="given_name",
    )
    assert given_name.value == "Jordan"

    entry = AuditEntry.objects.latest("timestamp")
    assert entry.action == Action.DENIED
    assert entry.decision_reason == "forbidden_fields"


@pytest.mark.django_db
def test_no_writable_policy_returns_403_and_writes_nothing(
    api_client: APIClient,
    seeded_person_id: uuid.UUID,
) -> None:
    """public_caller has empty writable set - any write attempt is denied."""
    before = ProfileField.objects.get(
        person_id=seeded_person_id,
        context=Context.PROFESSIONAL,
        key="given_name",
    ).value

    response = _auth_put(
        api_client,
        seeded_person_id,
        role=Role.PUBLIC_CALLER,
        context=Context.PROFESSIONAL,
        body={"fields": {"given_name": "Changed"}},
    )
    assert response.status_code == 403

    after = ProfileField.objects.get(
        person_id=seeded_person_id,
        context=Context.PROFESSIONAL,
        key="given_name",
    ).value
    assert after == before

    entry = AuditEntry.objects.latest("timestamp")
    assert entry.action == Action.DENIED
    assert entry.decision_reason == "no_writable_policy"


@pytest.mark.django_db
def test_write_throttle_returns_429_when_rate_exceeded(
    api_client: APIClient,
    seeded_person_id: uuid.UUID,
) -> None:
    """OWASP API4 - per-caller write rate limit returns 429 after quota exhausted.

    DRF copies DEFAULT_THROTTLE_RATES onto SimpleRateThrottle.THROTTLE_RATES at
    import time; patch the class attribute so the lowered test rate is honoured.
    """
    # Must own the fixture so the write reaches the throttle, not a 403.
    throttle_sub = DEFAULT_SEED_OWNER_SUB
    original_rates = IdentityWriteThrottle.THROTTLE_RATES
    try:
        IdentityWriteThrottle.THROTTLE_RATES = {"identity_write": "1/min"}
        cache.clear()

        token = mint_test_token(sub=throttle_sub, role=Role.SUBJECT)
        url = reverse(
            "identity-write",
            kwargs={"person_id": seeded_person_id, "context": Context.PROFESSIONAL},
        )
        body = {"fields": {"given_name": "First"}}

        first = api_client.put(
            url,
            body,
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        assert first.status_code == 200

        body["fields"]["given_name"] = "Second"
        second = api_client.put(
            url,
            body,
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        assert second.status_code == 429
    finally:
        IdentityWriteThrottle.THROTTLE_RATES = original_rates


@pytest.mark.django_db
def test_audit_endpoint_admin_allowed(
    api_client: APIClient,
    seeded_person_id: uuid.UUID,
) -> None:
    """Admin can list recent audit rows for a person."""
    _auth_put(
        api_client,
        seeded_person_id,
        role=Role.SUBJECT,
        context=Context.PROFESSIONAL,
        body={"fields": {"given_name": "Audited"}},
    )

    response = _auth_get_audit(api_client, seeded_person_id, role=Role.ADMIN)
    assert response.status_code == 200
    entries = response.json()
    assert len(entries) >= 1
    latest = entries[0]
    assert latest["action"] == Action.WRITE
    assert latest["person_id"] == str(seeded_person_id)
    assert set(latest["fields_disclosed"]) == {"given_name"}


@pytest.mark.django_db
def test_audit_endpoint_non_admin_denied(
    api_client: APIClient,
    seeded_person_id: uuid.UUID,
) -> None:
    """Non-admin callers receive 403 - role checked server-side, not from URL."""
    response = _auth_get_audit(api_client, seeded_person_id, role=Role.COLLEAGUE)
    assert response.status_code == 403


@pytest.mark.django_db
def test_audit_endpoint_response_contains_no_tokens_or_secrets(
    api_client: APIClient,
    seeded_person_id: uuid.UUID,
) -> None:
    """Audit list JSON has field keys and static reasons only - no bearer material."""
    token = mint_test_token(role=Role.SUBJECT)
    _auth_put(
        api_client,
        seeded_person_id,
        role=Role.SUBJECT,
        context=Context.PROFESSIONAL,
        body={"fields": {"given_name": "SecretValue-12345"}},
    )

    response = _auth_get_audit(api_client, seeded_person_id, role=Role.ADMIN)
    assert response.status_code == 200
    body = response.content.decode()
    assert token not in body
    assert "SecretValue-12345" not in body
    assert "Bearer " not in body
