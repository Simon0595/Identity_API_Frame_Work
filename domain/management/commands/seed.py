"""Synthetic domain seed for local dev and tests - all data is fictional."""

import os
import uuid

from django.core.management.base import BaseCommand

from domain.models import Context, Person, Policy, ProfileField, Role, Visibility

# Fixed UUID so re-running the command is idempotent (get_or_create by pk).
SEED_PERSON_ID = uuid.UUID("11111111-1111-4111-8111-111111111111")

# Owner 'sub' for the fixture person. Matches the test-token default so
# subject-role tests own the fixture. Override with SEED_OWNER_SUB to link a real
# Cognito user's sub for a live end-to-end demo.
DEFAULT_SEED_OWNER_SUB = "00000000-0000-4000-8000-000000000001"

PROFILE_FIELDS: list[tuple[str, str, str, str]] = [
    # (context, key, value, visibility)
    (Context.PROFESSIONAL, "given_name", "Jordan", Visibility.PUBLIC),
    (Context.PROFESSIONAL, "staff_id", "EMP-42", Visibility.RESTRICTED),
    (
        Context.PROFESSIONAL,
        "internal_notes",
        "Synthetic fixture only.",
        Visibility.CONFIDENTIAL,
    ),
    (Context.PERSONAL, "display_name", "J. Fixture", Visibility.PUBLIC),
    (Context.PERSONAL, "mobile", "555-0100", Visibility.RESTRICTED),
    (
        Context.PERSONAL,
        "home_address",
        "1 Example Lane, Fictional City",
        Visibility.CONFIDENTIAL,
    ),
]

# One row per role for the professional context (four roles from the spec).
POLICIES: list[tuple[str, str, list[str], list[str]]] = [
    (
        Role.SUBJECT,
        Context.PROFESSIONAL,
        [Visibility.PUBLIC, Visibility.RESTRICTED, Visibility.CONFIDENTIAL],
        [Visibility.PUBLIC, Visibility.RESTRICTED, Visibility.CONFIDENTIAL],
    ),
    (
        Role.COLLEAGUE,
        Context.PROFESSIONAL,
        [Visibility.PUBLIC, Visibility.RESTRICTED],
        [Visibility.PUBLIC],
    ),
    (
        Role.PUBLIC_CALLER,
        Context.PROFESSIONAL,
        [Visibility.PUBLIC],
        [],
    ),
    (
        Role.ADMIN,
        Context.PROFESSIONAL,
        [Visibility.PUBLIC, Visibility.RESTRICTED, Visibility.CONFIDENTIAL],
        [Visibility.PUBLIC, Visibility.RESTRICTED, Visibility.CONFIDENTIAL],
    ),
]


class Command(BaseCommand):
    help = "Load synthetic Person, profile fields, and Policy rows."

    def handle(self, *args: object, **options: object) -> None:
        owner_sub = os.environ.get("SEED_OWNER_SUB", DEFAULT_SEED_OWNER_SUB)
        person, _ = Person.objects.get_or_create(id=SEED_PERSON_ID)
        if person.owner_sub != owner_sub:
            person.owner_sub = owner_sub
            person.save(update_fields=["owner_sub"])

        for context, key, value, visibility in PROFILE_FIELDS:
            ProfileField.objects.update_or_create(
                person=person,
                context=context,
                key=key,
                defaults={"value": value, "visibility": visibility},
            )

        for role, context, readable, writable in POLICIES:
            Policy.objects.update_or_create(
                role=role,
                context=context,
                defaults={
                    "readable_visibilities": readable,
                    "writable_visibilities": writable,
                },
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded person {person.id}, "
                f"{len(PROFILE_FIELDS)} profile fields, "
                f"{len(POLICIES)} policies."
            )
        )
