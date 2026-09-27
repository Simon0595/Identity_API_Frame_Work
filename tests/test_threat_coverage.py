"""Map security tests to OWASP API risks and JWT threats."""

from __future__ import annotations

import inspect
import pkgutil
import re
import subprocess
import sys
import tomllib
from importlib import import_module
from pathlib import Path
from typing import Final

# (tests module basename without package prefix, test function name)
TestRef = tuple[str, str]

# Keys are labels; values are real test functions from the suite.
THREAT_MAP: Final[dict[str, list[TestRef]]] = {
    "OWASP API1 - BOLA": [
        ("test_read_redaction", "test_caller_with_no_visibility_gets_404_not_403"),
        ("test_read_redaction", "test_unknown_person_returns_404"),
        (
            "test_read_redaction",
            "test_read_returns_exactly_permitted_professional_fields",
        ),
        (
            "test_write_audit",
            "test_unauthorised_write_returns_403_and_writes_nothing",
        ),
    ],
    "OWASP API3 - BOPLA": [
        ("test_write_audit", "test_mass_assignment_forbidden_field_rejected"),
        (
            "test_write_audit",
            "test_mass_assignment_unexpected_top_level_field_rejected",
        ),
        ("test_permissions", "test_forbidden_request_keys_detects_mass_assignment"),
    ],
    "OWASP API4 - resource consumption (throttling)": [
        ("test_write_audit", "test_write_throttle_returns_429_when_rate_exceeded"),
        ("test_throttling", "test_anon_throttle_returns_429_when_rate_exceeded"),
        (
            "test_throttling",
            "test_authenticated_read_throttle_returns_429_when_rate_exceeded",
        ),
    ],
    "CORS - allowlist (no wildcard credentials)": [
        ("test_cors", "test_cors_allowed_origin_gets_access_control_allow_origin"),
        ("test_cors", "test_cors_disallowed_origin_omits_access_control_allow_origin"),
    ],
    "Security headers - CSP, Permissions-Policy, Referrer-Policy": [
        (
            "test_security_headers",
            "test_security_headers_present_on_health_response",
        ),
    ],
    "OWASP API5 - function-level authz": [
        ("test_write_audit", "test_audit_endpoint_admin_allowed"),
        ("test_write_audit", "test_audit_endpoint_non_admin_denied"),
    ],
    "OWASP API8 - error handling": [
        ("test_read_redaction", "test_invalid_token_rejected"),
        ("test_auth", "test_jwt_authentication_invalid_token_rejected"),
        (
            "test_write_audit",
            "test_audit_endpoint_response_contains_no_tokens_or_secrets",
        ),
        ("test_audit", "test_audit_records_must_not_contain_tokens_or_secrets"),
    ],
    "JWT - alg:none rejected": [
        ("test_auth", "test_token_alg_none_rejected"),
    ],
    "JWT - bad signature rejected": [
        ("test_auth", "test_token_bad_signature_rejected"),
    ],
    "JWT - exp rejected": [
        ("test_auth", "test_token_expired_rejected"),
    ],
    "JWT - aud rejected": [
        ("test_auth", "test_token_wrong_aud_rejected"),
    ],
    "JWT - iss rejected": [
        ("test_auth", "test_token_wrong_iss_rejected"),
    ],
}

REQUIRED_THREAT_LABELS: Final[frozenset[str]] = frozenset(THREAT_MAP)


def _discover_test_functions() -> set[TestRef]:
    """Collect (module_basename, test_fn) from tests/test_*.py - parametrised OK."""
    import tests

    found: set[TestRef] = set()
    for mod_info in pkgutil.iter_modules(tests.__path__):
        if not mod_info.name.startswith("test_"):
            continue
        mod = import_module(f"tests.{mod_info.name}")
        for name, _obj in inspect.getmembers(mod, inspect.isfunction):
            if name.startswith("test_"):
                found.add((mod_info.name, name))
    return found


def test_threat_map_references_existing_tests() -> None:
    """Fail if the map still points at a test we renamed or deleted."""
    discovered = _discover_test_functions()
    missing: list[str] = []
    for label, refs in THREAT_MAP.items():
        for module, fn in refs:
            if (module, fn) not in discovered:
                missing.append(f"{label}: {module}.{fn}")
    assert not missing, "Threat map points at missing tests:\n" + "\n".join(missing)


def test_threat_map_covers_required_owasp_and_jwt_categories() -> None:
    """Guard against accidental removal of an entire risk category from the map."""
    assert REQUIRED_THREAT_LABELS == frozenset(THREAT_MAP)


def test_coverage_config_targets_core_authz_logic() -> None:
    """Coverage is measured on core/, not config/."""
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    assert pyproject["tool"]["coverage"]["run"]["source"] == ["core"]
    assert pyproject["tool"]["coverage"]["report"]["fail_under"] >= 85


def test_core_authz_coverage_runs_and_reports_honest_percentage() -> None:
    """pytest --cov must succeed, print TOTAL, and stay below 100%."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--cov=core",
            "--cov-report=term",
            "-q",
            "--no-cov-on-fail",
            # Avoid recursive re-entry when this test spawns a child pytest.
            "-k",
            "not test_core_authz_coverage_runs_and_reports_honest_percentage",
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=Path(__file__).resolve().parents[1],
    )
    assert result.returncode == 0, result.stderr or result.stdout
    total_line = next(
        (line for line in result.stdout.splitlines() if line.startswith("TOTAL")),
        "",
    )
    assert total_line, "expected coverage TOTAL line in pytest output"
    match = re.search(r"(\d+)%", total_line)
    assert match, f"could not parse coverage percentage from: {total_line!r}"
    pct = int(match.group(1))
    assert 85 <= pct < 100, f"core authz coverage {pct}% looks gamed or too low"
