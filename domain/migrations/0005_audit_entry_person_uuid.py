# Audit target is a UUID, not a FK - denied lookups may reference unknown persons.

import uuid

from django.db import migrations, models


def _clear_audit_rows(apps: object, schema_editor: object) -> None:
    """Prototype-only: audit table is new; drop rows before FK -> UUID swap."""
    AuditEntry = apps.get_model("domain", "AuditEntry")  # type: ignore[attr-defined]
    AuditEntry.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("domain", "0004_audit_entry"),
    ]

    operations = [
        migrations.RunPython(_clear_audit_rows, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="auditentry",
            name="person",
        ),
        migrations.AddField(
            model_name="auditentry",
            name="person_id",
            field=models.UUIDField(
                default=uuid.UUID("00000000-0000-4000-8000-000000000000"),
                help_text=(
                    "Target identity UUID - may not exist (e.g. unknown person 404)."
                ),
            ),
            preserve_default=False,
        ),
    ]
