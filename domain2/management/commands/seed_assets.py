"""Synthetic domain2 seed for local dev and reuse tests - all data is fictional."""

import uuid

from django.core.management.base import BaseCommand

from domain2.models import (
    Asset,
    AssetAttribute,
    AssetContext,
    AssetPolicy,
    Role,
    Visibility,
)

# Fixed UUID so re-running the command is idempotent (get_or_create by pk).
SEED_ASSET_ID = uuid.UUID("22222222-2222-4222-8222-222222222222")

ASSET_ATTRIBUTES: list[tuple[str, str, str, str]] = [
    # (context, key, value, visibility)
    (AssetContext.OPERATIONAL, "asset_tag", "PUMP-7", Visibility.PUBLIC),
    (AssetContext.OPERATIONAL, "serial_number", "SN-8842", Visibility.RESTRICTED),
    (
        AssetContext.OPERATIONAL,
        "maintenance_notes",
        "Synthetic fixture only.",
        Visibility.CONFIDENTIAL,
    ),
    (AssetContext.INVENTORY, "location_code", "WH-A-12", Visibility.PUBLIC),
    (
        AssetContext.INVENTORY,
        "purchase_cost",
        "4200.00",
        Visibility.RESTRICTED,
    ),
    (
        AssetContext.INVENTORY,
        "vendor_contact",
        "555-0199",
        Visibility.CONFIDENTIAL,
    ),
]

# One row per role for operational context - mirrors domain professional policies.
POLICIES: list[tuple[str, str, list[str], list[str]]] = [
    (
        Role.SUBJECT,
        AssetContext.OPERATIONAL,
        [Visibility.PUBLIC, Visibility.RESTRICTED, Visibility.CONFIDENTIAL],
        [Visibility.PUBLIC, Visibility.RESTRICTED, Visibility.CONFIDENTIAL],
    ),
    (
        Role.COLLEAGUE,
        AssetContext.OPERATIONAL,
        [Visibility.PUBLIC, Visibility.RESTRICTED],
        [Visibility.PUBLIC],
    ),
    (
        Role.PUBLIC_CALLER,
        AssetContext.OPERATIONAL,
        [Visibility.PUBLIC],
        [],
    ),
    (
        Role.ADMIN,
        AssetContext.OPERATIONAL,
        [Visibility.PUBLIC, Visibility.RESTRICTED, Visibility.CONFIDENTIAL],
        [Visibility.PUBLIC, Visibility.RESTRICTED, Visibility.CONFIDENTIAL],
    ),
]


class Command(BaseCommand):
    help = "Load synthetic Asset, attributes, and AssetPolicy rows."

    def handle(self, *args: object, **options: object) -> None:
        asset, _ = Asset.objects.get_or_create(id=SEED_ASSET_ID)

        for context, key, value, visibility in ASSET_ATTRIBUTES:
            AssetAttribute.objects.update_or_create(
                asset=asset,
                context=context,
                key=key,
                defaults={"value": value, "visibility": visibility},
            )

        for role, context, readable, writable in POLICIES:
            AssetPolicy.objects.update_or_create(
                role=role,
                context=context,
                defaults={
                    "readable_visibilities": readable,
                    "writable_visibilities": writable,
                },
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded asset {asset.id}, "
                f"{len(ASSET_ATTRIBUTES)} attributes, "
                f"{len(POLICIES)} policies."
            )
        )
