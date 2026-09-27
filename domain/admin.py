"""Django admin registrations for domain inspection - no policy logic here."""

from django.contrib import admin
from django.http import HttpRequest

from domain.models import AuditEntry, Person, Policy, ProfileField


class ProfileFieldInline(admin.TabularInline):  # type: ignore[type-arg]
    """Show a person's attributes on the Person change page."""

    model = ProfileField
    extra = 0
    fields = ("context", "key", "value", "visibility")


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("id", "created_at", "updated_at")
    readonly_fields = ("id", "created_at", "updated_at")
    inlines = [ProfileFieldInline]


@admin.register(ProfileField)
class ProfileFieldAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("person", "context", "key", "visibility")
    list_filter = ("context", "visibility")
    search_fields = ("key", "value", "person__id")


@admin.register(Policy)
class PolicyAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("role", "context", "readable_visibilities", "writable_visibilities")
    list_filter = ("role", "context")


@admin.register(AuditEntry)
class AuditEntryAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    """Read-only - audit rows are append-only at the model layer."""

    list_display = (
        "timestamp",
        "action",
        "role",
        "person_id",
        "context",
        "caller_sub",
    )
    list_filter = ("action", "role", "context")
    readonly_fields = (
        "timestamp",
        "caller_sub",
        "role",
        "action",
        "person_id",
        "context",
        "fields_disclosed",
        "decision_reason",
    )

    def has_change_permission(
        self,
        request: HttpRequest,
        obj: AuditEntry | None = None,
    ) -> bool:
        return False

    def has_delete_permission(
        self,
        request: HttpRequest,
        obj: AuditEntry | None = None,
    ) -> bool:
        return False
