"""Audit service tests. Keys only, no tokens in the reason."""

import uuid

import pytest
from core.audit import (
    ACTION_DENIED,
    ACTION_READ,
    ACTION_WRITE,
    AuditRecord,
    AuditService,
)


class _MemoryStorage:
    """In-memory audit sink for unit tests - no ORM."""

    def __init__(self) -> None:
        self.rows: list[AuditRecord] = []

    def append(self, record: AuditRecord) -> None:
        self.rows.append(record)


def test_audit_service_persists_read_decision() -> None:
    """Happy path: read action with field keys and reason reaches storage."""
    storage = _MemoryStorage()
    service = AuditService(storage)
    person_id = uuid.uuid4()

    service.record(
        caller_sub="auth0|fixture-subject",
        role="subject",
        action=ACTION_READ,
        person_id=person_id,
        context="professional",
        fields=["given_name", "staff_id"],
        decision_reason="policy_allowed",
    )

    assert len(storage.rows) == 1
    row = storage.rows[0]
    assert row.action == ACTION_READ
    assert row.person_id == person_id
    assert row.fields == ("given_name", "staff_id")
    assert row.decision_reason == "policy_allowed"


@pytest.mark.parametrize("action", [ACTION_WRITE, ACTION_DENIED])
def test_audit_service_accepts_write_and_denied_actions(action: str) -> None:
    """All three action literals are valid audit events."""
    storage = _MemoryStorage()
    service = AuditService(storage)

    service.record(
        caller_sub="auth0|fixture-colleague",
        role="colleague",
        action=action,
        person_id=uuid.uuid4(),
        context="professional",
        fields=["given_name"],
        decision_reason="test_event",
    )

    assert storage.rows[0].action == action


def test_audit_service_rejects_invalid_action() -> None:
    """Unknown action strings fail closed before storage."""
    service = AuditService(_MemoryStorage())

    with pytest.raises(ValueError, match="Invalid audit action"):
        service.record(
            caller_sub="auth0|x",
            role="admin",
            action="delete",
            person_id=uuid.uuid4(),
            context="professional",
            fields=[],
            decision_reason="bad_action",
        )


def test_audit_service_rejects_empty_decision_reason() -> None:
    """Every decision must carry an explicit reason for the audit trail."""
    service = AuditService(_MemoryStorage())

    with pytest.raises(ValueError, match="decision_reason"):
        service.record(
            caller_sub="auth0|x",
            role="admin",
            action=ACTION_READ,
            person_id=uuid.uuid4(),
            context="professional",
            fields=["given_name"],
            decision_reason="",
        )


def test_audit_records_must_not_contain_tokens_or_secrets() -> None:
    """Reason text resembling JWT or Bearer material is rejected."""
    service = AuditService(_MemoryStorage())
    person_id = uuid.uuid4()

    with pytest.raises(ValueError, match="tokens or secrets"):
        service.record(
            caller_sub="auth0|x",
            role="colleague",
            action=ACTION_DENIED,
            person_id=person_id,
            context="professional",
            fields=[],
            decision_reason="token eyJhbGciOiJIUzI1NiJ9 leaked",
        )

    with pytest.raises(ValueError, match="tokens or secrets"):
        service.record(
            caller_sub="auth0|x",
            role="colleague",
            action=ACTION_DENIED,
            person_id=person_id,
            context="professional",
            fields=[],
            decision_reason="Header was Bearer abc123",
        )
