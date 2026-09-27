"""Save asset audit rows through the Django ORM."""

from core.audit import AuditRecord

from domain2.models import AssetAuditEntry


class OrmAuditStorage:
    """Append AuditRecord rows to the AssetAuditEntry table."""

    def append(self, record: AuditRecord) -> None:
        """Persist one immutable audit row - attribute keys only, never values."""
        AssetAuditEntry.objects.create(
            caller_sub=record.caller_sub,
            role=record.role,
            action=record.action,
            asset_id=record.person_id,
            context=record.context,
            fields_disclosed=list(record.fields),
            decision_reason=record.decision_reason,
        )
