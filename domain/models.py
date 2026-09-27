"""Domain schema - Person/ProfileField/Policy/AuditEntry. No auth or redaction here."""

import uuid
from typing import Any

from django.core.exceptions import ValidationError
from django.db import models


class Person(models.Model):
    """Identity anchor; attributes live on ProfileField, not on Person itself."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    owner_sub = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text=(
            "Identity 'sub' that owns this record. Empty means unowned: no "
            "subject-role caller can match it (deny by default)."
        ),
    )

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return str(self.id)


class Context(models.TextChoices):
    """Which life/work domain a profile attribute belongs to."""

    LEGAL = "legal", "Legal"
    PROFESSIONAL = "professional", "Professional"
    PERSONAL = "personal", "Personal"
    ONLINE = "online", "Online"


class Visibility(models.TextChoices):
    """Sensitivity class stored on the field; policy maps roles to readable classes."""

    PUBLIC = "public", "Public"
    RESTRICTED = "restricted", "Restricted"
    CONFIDENTIAL = "confidential", "Confidential"


class ProfileField(models.Model):
    """One attribute for a Person; names live here, not on Person itself."""

    person = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name="profile_fields",
    )
    context = models.CharField(max_length=32, choices=Context.choices)
    key = models.CharField(max_length=64)
    value = models.TextField()
    visibility = models.CharField(max_length=16, choices=Visibility.choices)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["person", "context", "key"],
                name="unique_person_context_key",
            ),
        ]
        ordering = ["person", "context", "key"]

    def __str__(self) -> str:
        return f"{self.person_id}:{self.context}.{self.key}"


class Role(models.TextChoices):
    """Caller role used as the policy lookup key (not enforced here)."""

    SUBJECT = "subject", "Subject"
    COLLEAGUE = "colleague", "Colleague"
    PUBLIC_CALLER = "public_caller", "Public caller"
    ADMIN = "admin", "Admin"


class Policy(models.Model):
    """Maps (role, context) to readable/writable visibility sets (data only)."""

    role = models.CharField(max_length=32, choices=Role.choices)
    context = models.CharField(max_length=32, choices=Context.choices)
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
                name="unique_role_context",
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
    """What the caller attempted. Written by the core audit service."""

    READ = "read", "Read"
    WRITE = "write", "Write"
    DENIED = "denied", "Denied"


class AuditEntry(models.Model):
    """Append-only access log; core writes rows, domain stores shape only."""

    timestamp = models.DateTimeField(auto_now_add=True)
    caller_sub = models.CharField(max_length=255)
    role = models.CharField(max_length=32, choices=Role.choices)
    action = models.CharField(max_length=16, choices=Action.choices)
    person_id = models.UUIDField(
        help_text="Target identity UUID - may not exist (e.g. unknown person 404).",
    )
    context = models.CharField(max_length=32, choices=Context.choices)
    fields_disclosed = models.JSONField(
        default=list,
        help_text="ProfileField keys returned or attempted.",
    )
    decision_reason = models.TextField()

    class Meta:
        ordering = ["-timestamp"]

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Reject updates - audit rows are insert-only at the model layer."""
        if self.pk is not None and AuditEntry.objects.filter(pk=self.pk).exists():
            raise ValidationError("Audit entries are immutable.")
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.action}@{self.timestamp}:{self.person_id}"
