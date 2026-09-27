"""Policy lookup from the ORM."""

import pytest
from core.policy import resolve_readable_visibilities, resolve_writable_visibilities
from django.core.management import call_command
from domain.models import Context, Policy, Role, Visibility
from domain.policy_lookup import OrmReadablePolicyLookup, OrmWritablePolicyLookup


@pytest.mark.django_db
def test_orm_lookup_returns_readable_list_for_existing_policy() -> None:
    """A policy row returns the visibility class strings."""
    Policy.objects.create(
        role=Role.COLLEAGUE,
        context=Context.PROFESSIONAL,
        readable_visibilities=[Visibility.PUBLIC, Visibility.RESTRICTED],
        writable_visibilities=[Visibility.PUBLIC],
    )
    lookup = OrmReadablePolicyLookup()
    result = lookup.readable_visibilities_for(Role.COLLEAGUE, Context.PROFESSIONAL)
    assert result == ["public", "restricted"]


@pytest.mark.django_db
def test_orm_lookup_returns_none_when_policy_row_missing() -> None:
    """Missing row returns None, so nothing is readable."""
    lookup = OrmReadablePolicyLookup()
    assert lookup.readable_visibilities_for(Role.COLLEAGUE, Context.PERSONAL) is None


@pytest.mark.django_db
def test_orm_lookup_with_core_resolve_matches_seed_policies() -> None:
    """Seeded professional policy matches what the resolver returns."""
    call_command("seed")
    lookup = OrmReadablePolicyLookup()

    public_readable = resolve_readable_visibilities(
        Role.PUBLIC_CALLER, Context.PROFESSIONAL, lookup
    )
    assert public_readable == frozenset({Visibility.PUBLIC})

    colleague_readable = resolve_readable_visibilities(
        Role.COLLEAGUE, Context.PROFESSIONAL, lookup
    )
    assert colleague_readable == frozenset(
        {Visibility.PUBLIC, Visibility.RESTRICTED}
    )


@pytest.mark.django_db
def test_orm_writable_lookup_returns_writable_list_for_existing_policy() -> None:
    """A policy row returns the writable visibility classes."""
    Policy.objects.create(
        role=Role.SUBJECT,
        context=Context.PERSONAL,
        readable_visibilities=[Visibility.PUBLIC, Visibility.RESTRICTED],
        writable_visibilities=[Visibility.PUBLIC, Visibility.RESTRICTED],
    )
    lookup = OrmWritablePolicyLookup()
    result = lookup.writable_visibilities_for(Role.SUBJECT, Context.PERSONAL)
    assert result == ["public", "restricted"]


@pytest.mark.django_db
def test_orm_writable_lookup_returns_none_when_policy_row_missing() -> None:
    """Missing row returns None, so nothing is writable."""
    lookup = OrmWritablePolicyLookup()
    assert lookup.writable_visibilities_for(Role.SUBJECT, Context.LEGAL) is None


@pytest.mark.django_db
def test_orm_writable_lookup_with_core_resolve_matches_seed_policies() -> None:
    """Seeded writable policy matches what the resolver returns."""
    call_command("seed")
    lookup = OrmWritablePolicyLookup()

    subject_writable = resolve_writable_visibilities(
        Role.SUBJECT, Context.PROFESSIONAL, lookup
    )
    assert subject_writable == frozenset(
        {Visibility.PUBLIC, Visibility.RESTRICTED, Visibility.CONFIDENTIAL}
    )

    public_writable = resolve_writable_visibilities(
        Role.PUBLIC_CALLER, Context.PROFESSIONAL, lookup
    )
    assert public_writable == frozenset()
