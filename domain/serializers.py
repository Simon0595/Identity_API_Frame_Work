"""Identity request/response shapes."""

from typing import Any
from uuid import UUID

from core.permissions import forbidden_request_keys
from rest_framework import serializers

from domain.models import AuditEntry, ProfileField


class RedactedIdentitySerializer(serializers.Serializer):  # type: ignore[type-arg]
    """Read payload after redaction."""

    id = serializers.UUIDField()
    context = serializers.CharField()  # type: ignore[assignment]
    fields = serializers.DictField(child=serializers.CharField())  # type: ignore[assignment]

    @classmethod
    def from_redacted(
        cls,
        person_id: UUID,
        context: str,
        redacted_fields: list[ProfileField],
    ) -> dict[str, Any]:
        """Build the payload from fields that already passed redaction."""
        return {
            "id": person_id,
            "context": context,
            "fields": {field.key: field.value for field in redacted_fields},
        }


class WritableIdentitySerializer(serializers.Serializer):  # type: ignore[type-arg]
    """Write request body - only keys on the server-side allow-list are accepted."""

    fields = serializers.DictField(  # type: ignore[assignment]
        child=serializers.CharField(allow_blank=True),
        allow_empty=True,
    )

    def __init__(self, *args: Any, allowed_keys: frozenset[str], **kwargs: Any) -> None:
        self._allowed_keys = allowed_keys
        super().__init__(*args, **kwargs)

    def run_validation(self, data: Any = serializers.empty) -> dict[str, Any]:
        """Only a fields object is allowed. Extra top-level keys are rejected."""
        if data is not serializers.empty and isinstance(data, dict):
            unexpected = frozenset(data.keys()) - frozenset({"fields"})
            if unexpected:
                raise serializers.ValidationError(
                    {"detail": "Invalid request body."},
                    code="unexpected_fields",
                )
        result: dict[str, Any] = super().run_validation(data)
        return result

    def validate_fields(self, value: dict[str, str]) -> dict[str, str]:
        """Deny keys outside the writable allow-list for this (role, context)."""
        requested = frozenset(value.keys())
        forbidden = forbidden_request_keys(requested, self._allowed_keys)
        if forbidden:
            raise serializers.ValidationError(
                {"detail": "Invalid request body."},
                code="forbidden_fields",
            )
        return value


class AuditEntrySerializer(serializers.ModelSerializer):  # type: ignore[type-arg]
    """Read-only audit rows for the admin list endpoint - keys only, never values."""

    class Meta:
        model = AuditEntry
        fields = (
            "timestamp",
            "caller_sub",
            "role",
            "action",
            "person_id",
            "context",
            "fields_disclosed",
            "decision_reason",
        )
        read_only_fields = fields
