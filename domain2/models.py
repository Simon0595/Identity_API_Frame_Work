"""Second domain schema - Asset/AssetAttribute. No auth or redaction here."""

import uuid
from typing import Any

from django.core.exceptions import ValidationError
from django.db import models


class Asset(models.Model):
    """Equipment/resource anchor; attributes live on AssetAttribute, not on Asset."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return str(self.id)


class AssetContext(models.TextChoices):
    """Life-cycle contexts for asset metadata - distinct from domain Context."""

    OPERATIONAL = "operational", "Operational"
    COMPLIANCE = "compliance", "Compliance"
    INVENTORY = "inventory", "Inventory"


class Visibility(models.TextChoices):
    """Sensitivity class - same values as domain; policy maps roles to these."""

    PUBLIC = "public", "Public"
    RESTRICTED = "restricted", "Restricted"
    CONFIDENTIAL = "confidential", "Confidential"


class AssetAttribute(models.Model):
    """One attribute on an asset."""

    asset = models.ForeignKey(
        Asset,
        on_delete=models.CASCADE,
        related_name="attributes",
    )
    context = models.CharField(max_length=32, choices=AssetContext.choices)
    key = models.CharField(max_length=64)
    value = models.TextField()
    visibility = models.CharField(max_length=16, choices=Visibility.choices)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["asset", "context", "key"],
                name="unique_asset_context_key",
            ),
        ]
        ordering = ["asset", "context", "key"]

    def __str__(self) -> str:
        return f"{self.asset_id}:{self.context}.{self.key}"


class Role(models.TextChoices):
    """Caller role - same strings as domain so JWT principals plug in unchanged."""

    SUBJECT = "subject", "Subject"
    COLLEAGUE = "colleague", "Colleague"
    PUBLIC_CALLER = "public_caller", "Public caller"
    ADMIN = "admin", "Admin"


class AssetPolicy(models.Model):
    """Maps (role, context) to readable/writable visibility sets for assets."""

    role = models.CharField(max_length=32, choices=Role.choices)
    context = models.CharField(max_length=32, choices=AssetContext.choices)
    readable_visibilities = models.JSONField(
        default=list,
        help_text="Visibility classes readable in this context.",
    )
    writable_visibilities = models.JSONField(
        default=list,
        help_text="Visibility classes writable in this context.",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["role", "context"],
                name="unique_asset_role_context",
            ),
        ]
        ordering = ["role", "context"]

    def clean(self) -> None:
        """JSON lists must hold Visibility enum values for core policy lookup."""
        super().clean()
        valid = set(Visibility.values)
        for field_name in ("readable_visibilities", "writable_visibilities"):
            values = getattr(self, field_name)
            if not isinstance(values, list):
                raise ValidationError(
                    {field_name: "Must be a list of visibility values."}
                )
            invalid = set(values) - valid
            if invalid:
                raise ValidationError(
                    {field_name: f"Invalid visibility values: {sorted(invalid)}"}
                )

    def __str__(self) -> str:
        return f"{self.role}@{self.context}"


class Action(models.TextChoices):
    """What the caller attempted - written by core audit service via domain2 adapter."""

    READ = "read", "Read"
    WRITE = "write", "Write"
    DENIED = "denied", "Denied"


class AssetAuditEntry(models.Model):
    """Append-only asset access log; core writes via storage adapter."""

    timestamp = models.DateTimeField(auto_now_add=True)
    caller_sub = models.CharField(max_length=255)
    role = models.CharField(max_length=32, choices=Role.choices)
    action = models.CharField(max_length=16, choices=Action.choices)
    asset_id = models.UUIDField(
        help_text="Target asset UUID (404 when unknown).",
    )
    context = models.CharField(max_length=32, choices=AssetContext.choices)
    fields_disclosed = models.JSONField(
        default=list,
        help_text="AssetAttribute keys returned or attempted.",
    )
    decision_reason = models.TextField()

    class Meta:
        ordering = ["-timestamp"]

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Reject updates - audit rows are insert-only at the model layer."""
        if self.pk is not None and AssetAuditEntry.objects.filter(pk=self.pk).exists():
            raise ValidationError("Audit entries are immutable.")
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.action}@{self.timestamp}:{self.asset_id}"
