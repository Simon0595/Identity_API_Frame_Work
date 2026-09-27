"""Audit rows actually land in the database."""

import uuid

import pytest
from core.audit import ACTION_READ, ACTION_WRITE, AuditService
from django.core.management import call_command
from domain.audit_storage import OrmAuditStorage
from domain.management.commands.seed import SEED_PERSON_ID
from domain.models import Action, AuditEntry, Context, Role


@pytest.fixture
def seeded_person_id(db: None) -> uuid.UUID:
    call_command("seed")
    return SEED_PERSON_ID


@pytest.mark.django_db
def test_orm_audit_storage_persists_read_via_audit_service(
    seeded_person_id: uuid.UUID,
) -> None:
    """AuditService + OrmAuditStorage writes one append-only audit row."""
    service = AuditService(OrmAuditStorage())

    service.record(
        caller_sub="auth0|fixture-subject",
        role=Role.SUBJECT,
        action=ACTION_READ,
        person_id=seeded_person_id,
        context=Context.PROFESSIONAL,
        fields=["given_name", "staff_id"],
        decision_reason="policy_allowed",
    )

    assert AuditEntry.objects.count() == 1
    entry = AuditEntry.objects.get()
    assert entry.caller_sub == "auth0|fixture-subject"
    assert entry.role == Role.SUBJECT
    assert entry.action == Action.READ
    assert entry.person_id == seeded_person_id
    assert entry.context == Context.PROFESSIONAL
    assert entry.fields_disclosed == ["given_name", "staff_id"]
    assert entry.decision_reason == "policy_allowed"
    assert entry.timestamp is not None


@pytest.mark.django_db
def test_audit_records_contain_no_field_values_or_tokens(
    seeded_person_id: uuid.UUID,
) -> None:
    """Stored rows hold keys and static reasons only - never profile values or JWTs."""
    service = AuditService(OrmAuditStorage())
    secret_value = "super-secret-home-address"
    jwt_fragment = "eyJhbGciOiJIUzI1NiJ9"

    service.record(
        caller_sub="auth0|fixture-admin",
        role=Role.ADMIN,
        action=ACTION_WRITE,
        person_id=seeded_person_id,
        context=Context.PROFESSIONAL,
        fields=["given_name"],
        decision_reason="write_allowed",
    )

    entry = AuditEntry.objects.get()
    stored_blob = (
        entry.caller_sub
        + entry.decision_reason
        + "".join(entry.fields_disclosed)
        + entry.role
        + entry.action
    )
    assert secret_value not in stored_blob
    assert jwt_fragment not in stored_blob
    assert "Bearer " not in stored_blob
