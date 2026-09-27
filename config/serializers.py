"""Project-level serializers - SPA helpers with no domain model coupling."""

from typing import Any

from domain.models import Role
from rest_framework import serializers


class DevLoginRequestSerializer(serializers.Serializer):  # type: ignore[type-arg]
    """POST body for offline dev login - explicit allow-list, no mass assignment."""

    role = serializers.ChoiceField(choices=Role.choices)
    sub = serializers.CharField(max_length=255, required=False)

    def run_validation(self, data: Any = serializers.empty) -> dict[str, object]:
        """Reject top-level keys other than role/sub - anti mass-assignment."""
        if data is not serializers.empty and isinstance(data, dict):
            unexpected = frozenset(data.keys()) - frozenset({"role", "sub"})
            if unexpected:
                raise serializers.ValidationError(
                    {"detail": "Invalid request body."},
                    code="unexpected_fields",
                )
        result: dict[str, object] = super().run_validation(data)
        return result

    def validate(self, attrs: dict[str, object]) -> dict[str, object]:
        if "sub" not in attrs:
            # Default matches seed owner sub so subject-role demos own the fixture.
            attrs["sub"] = "00000000-0000-4000-8000-000000000001"
        return attrs
