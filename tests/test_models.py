"""Model-level tests for the domain schema."""

import uuid

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone
from domain.models import (
    Action,
    AuditEntry,
    Context,
    Person,
    Policy,
    ProfileField,
    Role,
    Visibility,
)


@pytest.mark.django_db
def test_person_primary_key_is_uuid() -> None:
    """Person.id must be a UUID so identities are opaque and globally unique."""
    person = Person.objects.create()
    assert isinstance(person.id, uuid.UUID)


@pytest.mark.django_db
def test_person_timestamps_populate_on_create() -> None:
    """created_at/updated_at are set by the DB layer on first save."""
    before = timezone.now()
    person = Person.objects.create()
    after = timezone.now()
    assert before <= person.created_at <= after
    assert before <= person.updated_at <= after


@pytest.mark.django_db
def test_profile_field_unique_together_person_context_key() -> None:
    """Duplicate (person, context, key) must fail at the DB layer."""
    person = Person.objects.create()
    ProfileField.objects.create(
        person=person,
        context=Context.LEGAL,
        key="given_name",
        value="Alex",
        visibility=Visibility.PUBLIC,
    )
    with pytest.raises(IntegrityError):
        ProfileField.objects.create(
            person=person,
            context=Context.LEGAL,
            key="given_name",
            value="Other",
            visibility=Visibility.RESTRICTED,
        )


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("context", "not_a_context"),
        ("visibility", "top_secret"),
    ],
)
def test_profile_field_rejects_invalid_enum_values(
    field_name: str,
    invalid_value: str,
) -> None:
    """CharField choices are enforced via full_clean(), not raw SQL inserts."""
    person = Person.objects.create()
    field = ProfileField(
        person=person,
        context=Context.PROFESSIONAL,
        key="staff_id",
        value="EMP-001",
        visibility=Visibility.RESTRICTED,
    )
    setattr(field, field_name, invalid_value)
    with pytest.raises(ValidationError):
        field.full_clean()


@pytest.mark.django_db
def test_policy_unique_together_role_context() -> None:
    """One policy row per (role, context) - duplicates fail at the DB layer."""
    Policy.objects.create(
        role=Role.SUBJECT,
        context=Context.PROFESSIONAL,
        readable_visibilities=[Visibility.PUBLIC, Visibility.RESTRICTED],
        writable_visibilities=[Visibility.PUBLIC],
    )
    with pytest.raises(IntegrityError):
        Policy.objects.create(
            role=Role.SUBJECT,
            context=Context.PROFESSIONAL,
            readable_visibilities=[Visibility.PUBLIC],
            writable_visibilities=[],
        )


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("role", "superuser"),
        ("context", "not_a_context"),
    ],
)
def test_policy_rejects_invalid_enum_values(
    field_name: str,
    invalid_value: str,
) -> None:
    """Role and context CharField choices are enforced via full_clean()."""
    policy = Policy(
        role=Role.COLLEAGUE,
        context=Context.LEGAL,
        readable_visibilities=[Visibility.PUBLIC],
        writable_visibilities=[],
    )
    setattr(policy, field_name, invalid_value)
    with pytest.raises(ValidationError):
        policy.full_clean()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "field_name",
    ["readable_visibilities", "writable_visibilities"],
)
def test_policy_rejects_invalid_visibility_in_json_lists(field_name: str) -> None:
    """Visibility sets are JSON lists validated in Policy.clean()."""
    policy = Policy(
        role=Role.ADMIN,
        context=Context.PERSONAL,
        readable_visibilities=[Visibility.PUBLIC],
        writable_visibilities=[Visibility.RESTRICTED],
    )
    setattr(policy, field_name, ["top_secret"])
    with pytest.raises(ValidationError):
        policy.full_clean()


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("role", "superuser"),
        ("context", "not_a_context"),
        ("action", "delete"),
    ],
)
def test_audit_entry_rejects_invalid_enum_values(
    field_name: str,
    invalid_value: str,
) -> None:
    """Role, context, and action CharField choices are enforced via full_clean()."""
    person = Person.objects.create()
    entry = AuditEntry(
        caller_sub="auth0|fixture-subject",
        role=Role.SUBJECT,
        action=Action.READ,
        person_id=person.id,
        context=Context.LEGAL,
        fields_disclosed=["given_name"],
        decision_reason="allowed",
    )
    setattr(entry, field_name, invalid_value)
    with pytest.raises(ValidationError):
        entry.full_clean()


@pytest.mark.django_db
def test_audit_entry_is_immutable_after_create() -> None:
    """Updates are blocked in save() so the log stays append-only."""
    person = Person.objects.create()
    entry = AuditEntry.objects.create(
        caller_sub="auth0|fixture-subject",
        role=Role.SUBJECT,
        action=Action.READ,
        person_id=person.id,
        context=Context.LEGAL,
        fields_disclosed=["given_name"],
        decision_reason="allowed",
    )
    entry.decision_reason = "tampered"
    with pytest.raises(ValidationError, match="immutable"):
        entry.save()


@pytest.mark.django_db
def test_seed_command_loads_expected_counts() -> None:
    """Seed creates one Person, fields in two contexts, and four Policy rows."""
    from django.core.management import call_command

    call_command("seed")

    assert Person.objects.count() == 1
    person = Person.objects.get()
    fields = ProfileField.objects.filter(person=person)
    assert fields.count() == 6
    assert fields.values_list("context", flat=True).distinct().count() == 2
    assert set(fields.values_list("visibility", flat=True)) == {
        Visibility.PUBLIC,
        Visibility.RESTRICTED,
        Visibility.CONFIDENTIAL,
    }
    assert Policy.objects.count() == 4
    assert set(Policy.objects.values_list("role", flat=True)) == {
        Role.SUBJECT,
        Role.COLLEAGUE,
        Role.PUBLIC_CALLER,
        Role.ADMIN,
    }
