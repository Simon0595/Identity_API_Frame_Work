"""Second domain uses the same policy and redaction code."""

import ast
import uuid
from pathlib import Path
from typing import Any

import pytest
from core.auth.testing import mint_test_token
from django.core.management import call_command
from django.urls import reverse
from domain2.management.commands.seed_assets import SEED_ASSET_ID
from domain2.models import AssetContext, Role
from rest_framework.test import APIClient

REPO_ROOT = Path(__file__).resolve().parent.parent
CORE_DIR = REPO_ROOT / "core"

# Operational policies mirror domain professional - same visibilities, new keys.
OPERATIONAL_FIELD_EXPECTATIONS: list[tuple[str, frozenset[str]]] = [
    (Role.SUBJECT, frozenset({"asset_tag", "serial_number", "maintenance_notes"})),
    (Role.COLLEAGUE, frozenset({"asset_tag", "serial_number"})),
    (Role.PUBLIC_CALLER, frozenset({"asset_tag"})),
    (Role.ADMIN, frozenset({"asset_tag", "serial_number", "maintenance_notes"})),
]

ALL_OPERATIONAL_KEYS = frozenset({"asset_tag", "serial_number", "maintenance_notes"})


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def seeded_asset_id(db: None) -> uuid.UUID:
    """Synthetic domain2 fixture - shared by reuse redaction tests."""
    call_command("seed_assets")
    return SEED_ASSET_ID


def _auth_get_asset(
    client: APIClient,
    asset_id: uuid.UUID,
    *,
    role: str,
    context: str,
) -> Any:
    token = mint_test_token(role=role)
    url = reverse("asset-read", kwargs={"asset_id": asset_id})
    return client.get(url, {"context": context}, HTTP_AUTHORIZATION=f"Bearer {token}")


def _domain_imports_in_core() -> list[str]:
    """Return human-readable violations if any core module imports domain or domain2."""
    violations: list[str] = []
    for path in sorted(CORE_DIR.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    mod = alias.name
                    if mod == "domain" or mod.startswith("domain."):
                        rel = path.relative_to(REPO_ROOT)
                        violations.append(f"{rel}: import {mod}")
                    if mod == "domain2" or mod.startswith("domain2."):
                        rel = path.relative_to(REPO_ROOT)
                        violations.append(f"{rel}: import {mod}")
            elif isinstance(node, ast.ImportFrom) and node.module:
                mod = node.module
                if mod == "domain" or mod.startswith("domain."):
                    violations.append(
                        f"{path.relative_to(REPO_ROOT)}: from {mod} import ..."
                    )
                if mod == "domain2" or mod.startswith("domain2."):
                    violations.append(
                        f"{path.relative_to(REPO_ROOT)}: from {mod} import ..."
                    )
    return violations


def test_core_modules_do_not_import_domain_packages() -> None:
    """core/ must not import domain or domain2."""
    assert _domain_imports_in_core() == []


@pytest.mark.django_db
@pytest.mark.parametrize(("role", "expected_keys"), OPERATIONAL_FIELD_EXPECTATIONS)
def test_asset_read_returns_exactly_permitted_operational_fields(
    api_client: APIClient,
    seeded_asset_id: uuid.UUID,
    role: str,
    expected_keys: frozenset[str],
) -> None:
    """Asset read uses the same redaction. Permitted keys match the policy rows."""
    response = _auth_get_asset(
        api_client,
        seeded_asset_id,
        role=role,
        context=AssetContext.OPERATIONAL,
    )
    assert response.status_code == 200
    body = response.json()
    assert set(body["fields"].keys()) == expected_keys
    for excluded in ALL_OPERATIONAL_KEYS - expected_keys:
        assert excluded not in body["fields"]


@pytest.mark.django_db
@pytest.mark.parametrize("role", [r for r, _ in Role.choices])
def test_asset_inventory_context_without_policy_returns_404(
    api_client: APIClient,
    seeded_asset_id: uuid.UUID,
    role: str,
) -> None:
    """Inventory has attributes but no policy row - 404, not a partial leak."""
    response = _auth_get_asset(
        api_client,
        seeded_asset_id,
        role=role,
        context=AssetContext.INVENTORY,
    )
    assert response.status_code == 404
