"""Read path + redaction integration tests - policy, 404 rule, auth."""

import uuid
from typing import Any

import pytest
from core.auth.testing import mint_test_token
from django.core.management import call_command
from django.urls import reverse
from domain.management.commands.seed import SEED_PERSON_ID
from domain.models import Action, AuditEntry, Context, Role
from rest_framework.test import APIClient


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def seeded_person_id(db: None) -> uuid.UUID:
    """Synthetic fixture person - all policy/field tests share seed data."""
    call_command("seed")
    return SEED_PERSON_ID


def _auth_get(
    client: APIClient,
    person_id: uuid.UUID,
    *,
    role: str,
    context: str,
) -> Any:
    token = mint_test_token(role=role)
    url = reverse("identity-read", kwargs={"person_id": person_id})
    return client.get(url, {"context": context}, HTTP_AUTHORIZATION=f"Bearer {token}")


# All four seeded professional policies and their permitted field keys.
PROFESSIONAL_FIELD_EXPECTATIONS: list[tuple[str, frozenset[str]]] = [
    (Role.SUBJECT, frozenset({"given_name", "staff_id", "internal_notes"})),
    (Role.COLLEAGUE, frozenset({"given_name", "staff_id"})),
    (Role.PUBLIC_CALLER, frozenset({"given_name"})),
    (Role.ADMIN, frozenset({"given_name", "staff_id", "internal_notes"})),
]

ALL_PROFESSIONAL_KEYS = frozenset({"given_name", "staff_id", "internal_notes"})


@pytest.mark.django_db
@pytest.mark.parametrize(("role", "expected_keys"), PROFESSIONAL_FIELD_EXPECTATIONS)
def test_read_returns_exactly_permitted_professional_fields(
    api_client: APIClient,
    seeded_person_id: uuid.UUID,
    role: str,
    expected_keys: frozenset[str],
) -> None:
    """Each (role, professional) pair exposes exactly the policy-permitted field set."""
    response = _auth_get(
        api_client,
        seeded_person_id,
        role=role,
        context=Context.PROFESSIONAL,
    )
    assert response.status_code == 200
    body = response.json()
    assert set(body["fields"].keys()) == expected_keys
    for excluded in ALL_PROFESSIONAL_KEYS - expected_keys:
        assert excluded not in body["fields"]


@pytest.mark.django_db
@pytest.mark.parametrize("role", [r for r, _ in Role.choices])
def test_read_personal_context_without_policy_returns_404(
    api_client: APIClient,
    seeded_person_id: uuid.UUID,
    role: str,
) -> None:
    """No (role, personal) policy row - caller may see nothing -> 404, not empty 200."""
    response = _auth_get(
        api_client,
        seeded_person_id,
        role=role,
        context=Context.PERSONAL,
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_caller_with_no_visibility_gets_404_not_403(
    api_client: APIClient,
    seeded_person_id: uuid.UUID,
) -> None:
    """Existence non-disclosure: zero readable visibilities must not return 403."""
    response = _auth_get(
        api_client,
        seeded_person_id,
        role=Role.COLLEAGUE,
        context=Context.PERSONAL,
    )
    assert response.status_code == 404
    assert response.status_code != 403


@pytest.mark.django_db
def test_declared_context_does_not_widen_visibility(
    api_client: APIClient,
    seeded_person_id: uuid.UUID,
) -> None:
    """
    Declared context is lookup input only - personal context does not grant
    personal fields when no (colleague, personal) policy exists.
    """
    professional = _auth_get(
        api_client,
        seeded_person_id,
        role=Role.COLLEAGUE,
        context=Context.PROFESSIONAL,
    )
    assert professional.status_code == 200
    assert "display_name" not in professional.json()["fields"]

    personal = _auth_get(
        api_client,
        seeded_person_id,
        role=Role.COLLEAGUE,
        context=Context.PERSONAL,
    )
    assert personal.status_code == 404


@pytest.mark.django_db
def test_colleague_cannot_read_confidential_field(
    api_client: APIClient,
    seeded_person_id: uuid.UUID,
) -> None:
    """Confidential visibility never appears for a role limited to public+restricted."""
    response = _auth_get(
        api_client,
        seeded_person_id,
        role=Role.COLLEAGUE,
        context=Context.PROFESSIONAL,
    )
    assert response.status_code == 200
    assert "internal_notes" not in response.json()["fields"]


@pytest.mark.django_db
def test_unknown_person_read_is_audited_as_denied(
    api_client: APIClient,
    seeded_person_id: uuid.UUID,
) -> None:
    """404 for missing person still records audit against the requested UUID."""
    unknown_id = uuid.uuid4()
    assert unknown_id != seeded_person_id
    response = _auth_get(
        api_client,
        unknown_id,
        role=Role.ADMIN,
        context=Context.PROFESSIONAL,
    )
    assert response.status_code == 404
    entry = AuditEntry.objects.get()
    assert entry.action == Action.DENIED
    assert entry.person_id == unknown_id
    assert entry.decision_reason == "person_not_found"


@pytest.mark.django_db
def test_unknown_person_returns_404(
    api_client: APIClient,
    seeded_person_id: uuid.UUID,
) -> None:
    """Missing person is indistinguishable from no visibility - 404 only."""
    unknown_id = uuid.uuid4()
    assert unknown_id != seeded_person_id
    response = _auth_get(
        api_client,
        unknown_id,
        role=Role.ADMIN,
        context=Context.PROFESSIONAL,
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_unauthenticated_request_rejected(
    api_client: APIClient,
    seeded_person_id: uuid.UUID,
) -> None:
    """auth: missing bearer token -> 401."""
    url = reverse("identity-read", kwargs={"person_id": seeded_person_id})
    response = api_client.get(url, {"context": Context.PROFESSIONAL})
    assert response.status_code == 401


@pytest.mark.django_db
def test_invalid_token_rejected(
    api_client: APIClient,
    seeded_person_id: uuid.UUID,
) -> None:
    """auth: bad JWT -> 401 with generic error (token never echoed)."""
    url = reverse("identity-read", kwargs={"person_id": seeded_person_id})
    response = api_client.get(
        url,
        {"context": Context.PROFESSIONAL},
        HTTP_AUTHORIZATION="Bearer not-a-valid-jwt",
    )
    assert response.status_code == 401
    assert "not-a-valid-jwt" not in response.content.decode()


@pytest.mark.django_db
def test_successful_read_creates_audit_entry_with_disclosed_field_keys(
    api_client: APIClient,
    seeded_person_id: uuid.UUID,
) -> None:
    """Every authorised read is audited with field keys only - never values."""
    response = _auth_get(
        api_client,
        seeded_person_id,
        role=Role.COLLEAGUE,
        context=Context.PROFESSIONAL,
    )
    assert response.status_code == 200
    entry = AuditEntry.objects.get()
    assert entry.action == Action.READ
    assert entry.decision_reason == "policy_allowed"
    assert set(entry.fields_disclosed) == {"given_name", "staff_id"}
    assert "Jordan" not in entry.decision_reason
    assert "EMP-42" not in "".join(entry.fields_disclosed)


@pytest.mark.django_db
def test_denied_read_creates_audit_entry(
    api_client: APIClient,
    seeded_person_id: uuid.UUID,
) -> None:
    """404 read paths still append a denied audit row with a static reason."""
    response = _auth_get(
        api_client,
        seeded_person_id,
        role=Role.COLLEAGUE,
        context=Context.PERSONAL,
    )
    assert response.status_code == 404
    entry = AuditEntry.objects.get()
    assert entry.action == Action.DENIED
    assert entry.decision_reason == "no_readable_policy"
    assert entry.fields_disclosed == []


@pytest.mark.django_db
def test_public_caller_never_sees_restricted_or_confidential_values(
    api_client: APIClient,
    seeded_person_id: uuid.UUID,
) -> None:
    """Negative path: restricted/confidential keys and values absent from body."""
    response = _auth_get(
        api_client,
        seeded_person_id,
        role=Role.PUBLIC_CALLER,
        context=Context.PROFESSIONAL,
    )
    assert response.status_code == 200
    fields = response.json()["fields"]
    assert set(fields.keys()) == {"given_name"}
    assert "EMP-42" not in fields.values()
    assert "Synthetic fixture only." not in fields.values()
