"""Save audit rows through the Django ORM."""

from core.audit import AuditRecord

from domain.models import AuditEntry


class OrmAuditStorage:
    """Append AuditRecord rows to the AuditEntry table."""

    def append(self, record: AuditRecord) -> None:
        """Persist one immutable audit row - field keys only, never values."""
        AuditEntry.objects.create(
            caller_sub=record.caller_sub,
            role=record.role,
            action=record.action,
            person_id=record.person_id,
            context=record.context,
            fields_disclosed=list(record.fields),
            decision_reason=record.decision_reason,
        )
