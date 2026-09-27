"""Asset read payload."""

from typing import Any
from uuid import UUID

from rest_framework import serializers

from domain2.models import AssetAttribute


class RedactedAssetSerializer(serializers.Serializer):  # type: ignore[type-arg]
    """Read payload after redaction."""

    id = serializers.UUIDField()
    context = serializers.CharField()  # type: ignore[assignment]
    fields = serializers.DictField(child=serializers.CharField())  # type: ignore[assignment]

    @classmethod
    def from_redacted(
        cls,
        asset_id: UUID,
        context: str,
        redacted_attributes: list[AssetAttribute],
    ) -> dict[str, Any]:
        """Build the payload from attributes that already passed redaction."""
        return {
            "id": asset_id,
            "context": context,
            "fields": {attr.key: attr.value for attr in redacted_attributes},
        }
