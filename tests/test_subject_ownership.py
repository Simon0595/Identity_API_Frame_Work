"""Object-level authorisation tests - subject role is owner-scoped."""

import uuid
from typing import Any

import pytest
from core.auth.testing import mint_test_token
from django.core.management import call_command
from django.urls import reverse
from domain.management.commands.seed import DEFAULT_SEED_OWNER_SUB, SEED_PERSON_ID
from domain.models import Action, AuditEntry, Context, Person, ProfileField, Role
from rest_framework.test import APIClient

OTHER_SUB = "00000000-0000-4000-8000-0000000000ff"


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def seeded_person_id(db: None) -> uuid.UUID:
    """Fixture person owned by DEFAULT_SEED_OWNER_SUB (see seed command)."""
    call_command("seed")
    return SEED_PERSON_ID


def _read(
    client: APIClient,
    person_id: uuid.UUID,
    *,
    sub: str,
    role: str,
    context: str,
) -> Any:
    token = mint_test_token(sub=sub, role=role)
    url = reverse("identity-read", kwargs={"person_id": person_id})
    return client.get(url, {"context": context}, HTTP_AUTHORIZATION=f"Bearer {token}")


def _write(
    client: APIClient,
    person_id: uuid.UUID,
    *,
    sub: str,
    role: str,
    context: str,
    body: dict[str, Any],
) -> Any:
    token = mint_test_token(sub=sub, role=role)
    url = reverse(
        "identity-write",
        kwargs={"person_id": person_id, "context": context},
    )
    return client.put(
        url, body, format="json", HTTP_AUTHORIZATION=f"Bearer {token}"
    )


@pytest.mark.django_db
def test_subject_reads_own_record_200(
    api_client: APIClient,
    seeded_person_id: uuid.UUID,
) -> None:
    """Owner sub matches -> 200 with the full subject professional field set."""
    response = _read(
        api_client,
        seeded_person_id,
        sub=DEFAULT_SEED_OWNER_SUB,
        role=Role.SUBJECT,
        context=Context.PROFESSIONAL,
    )
    assert response.status_code == 200
    assert set(response.json()["fields"].keys()) == {
        "given_name",
        "staff_id",
        "internal_notes",
    }


@pytest.mark.django_db
def test_subject_cannot_read_non_owned_record_404(
    api_client: APIClient,
    seeded_person_id: uuid.UUID,
) -> None:
    """Subject with a different sub -> 404 (not 403/200), audited not_owner."""
    response = _read(
        api_client,
        seeded_person_id,
        sub=OTHER_SUB,
        role=Role.SUBJECT,
        context=Context.PROFESSIONAL,
    )
    assert response.status_code == 404
    assert response.status_code != 403

    entry = AuditEntry.objects.latest("timestamp")
    assert entry.action == Action.DENIED
    assert entry.decision_reason == "not_owner"
    assert entry.caller_sub == OTHER_SUB
    assert entry.fields_disclosed == []


@pytest.mark.django_db
def test_subject_cannot_write_non_owned_record_403(
    api_client: APIClient,
    seeded_person_id: uuid.UUID,
) -> None:
    """Different-sub subject token: 403, nothing persists, audited not_owner."""
    before = ProfileField.objects.get(
        person_id=seeded_person_id,
        context=Context.PROFESSIONAL,
        key="given_name",
    ).value

    response = _write(
        api_client,
        seeded_person_id,
        sub=OTHER_SUB,
        role=Role.SUBJECT,
        context=Context.PROFESSIONAL,
        body={"fields": {"given_name": "Hijacked"}},
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
    assert entry.decision_reason == "not_owner"


@pytest.mark.django_db
@pytest.mark.parametrize("role", [Role.COLLEAGUE, Role.PUBLIC_CALLER, Role.ADMIN])
def test_non_subject_roles_are_not_owner_scoped(
    api_client: APIClient,
    seeded_person_id: uuid.UUID,
    role: str,
) -> None:
    """colleague/public_caller/admin read the record regardless of ownership sub."""
    response = _read(
        api_client,
        seeded_person_id,
        sub=OTHER_SUB,
        role=role,
        context=Context.PROFESSIONAL,
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_unowned_person_denies_subject_read_and_write(
    api_client: APIClient,
    seeded_person_id: uuid.UUID,
) -> None:
    """Empty owner_sub: subject read is 404, write is 403."""
    unowned = Person.objects.create(owner_sub="")

    read = _read(
        api_client,
        unowned.id,
        sub=DEFAULT_SEED_OWNER_SUB,
        role=Role.SUBJECT,
        context=Context.PROFESSIONAL,
    )
    assert read.status_code == 404

    write = _write(
        api_client,
        unowned.id,
        sub=DEFAULT_SEED_OWNER_SUB,
        role=Role.SUBJECT,
        context=Context.PROFESSIONAL,
        body={"fields": {"given_name": "X"}},
    )
    assert write.status_code == 403
