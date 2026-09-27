"""Append-only access log. Stores field keys, never values or tokens."""

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

# Same strings as domain.models.Action, copied so this file does not import domain.
ACTION_READ = "read"
ACTION_WRITE = "write"
ACTION_DENIED = "denied"

ALLOWED_ACTIONS = frozenset({ACTION_READ, ACTION_WRITE, ACTION_DENIED})

# Fail closed if free-text reasons look like they carry bearer material.
_FORBIDDEN_REASON_FRAGMENTS = ("eyJ", "Bearer ")


@dataclass(frozen=True, slots=True)
class AuditRecord:
    """Immutable audit row - field keys only, never values or secrets."""

    caller_sub: str
    role: str
    action: str
    person_id: UUID
    context: str
    fields: tuple[str, ...]
    decision_reason: str


class AuditStorage(Protocol):
    """domain supplies ORM-backed append in the view layer."""

    def append(self, record: AuditRecord) -> None:
        """Persist one audit row."""


def _validate_record(record: AuditRecord) -> None:
    """Reject incomplete or secret-bearing rows before they reach storage."""
    if record.action not in ALLOWED_ACTIONS:
        raise ValueError(f"Invalid audit action: {record.action!r}")
    if not record.caller_sub or not record.role:
        raise ValueError("caller_sub and role are required")
    if not record.context:
        raise ValueError("context is required")
    if not record.decision_reason:
        raise ValueError("decision_reason is required")
    reason_lower = record.decision_reason.lower()
    for fragment in _FORBIDDEN_REASON_FRAGMENTS:
        if fragment.lower() in reason_lower:
            raise ValueError("decision_reason must not contain tokens or secrets")


class AuditService:
    """Append-only audit trail for read, write, and denied decisions."""

    def __init__(self, storage: AuditStorage) -> None:
        self._storage = storage

    def record(
        self,
        *,
        caller_sub: str,
        role: str,
        action: str,
        person_id: UUID,
        context: str,
        fields: list[str],
        decision_reason: str,
    ) -> None:
        """
        Persist one immutable audit entry.

        fields must be profile-field keys only - never values. Callers supply
        static decision_reason strings; raw JWTs or secrets are rejected.
        """
        record = AuditRecord(
            caller_sub=caller_sub,
            role=role,
            action=action,
            person_id=person_id,
            context=context,
            fields=tuple(fields),
            decision_reason=decision_reason,
        )
        _validate_record(record)
        self._storage.append(record)
