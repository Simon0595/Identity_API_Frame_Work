"""Write-key allow-list tests."""

from dataclasses import dataclass

from core.permissions import allowed_write_keys, forbidden_request_keys


@dataclass(frozen=True)
class _StubField:
    """Test double - key + visibility only, no domain imports."""

    key: str
    visibility: str


def test_allowed_write_keys_returns_writable_keys_only() -> None:
    """Happy path: only keys whose visibility class is in the writable set."""
    fields = [
        _StubField("given_name", "public"),
        _StubField("staff_id", "restricted"),
        _StubField("internal_notes", "confidential"),
    ]
    writable = frozenset({"public", "restricted"})

    assert allowed_write_keys(fields, writable) == frozenset({"given_name", "staff_id"})


def test_allowed_write_keys_empty_writable_set_denies_by_default() -> None:
    """No writable visibilities -> no keys may be written (403 path downstream)."""
    fields = [_StubField("given_name", "public")]
    assert allowed_write_keys(fields, frozenset()) == frozenset()


def test_forbidden_request_keys_detects_mass_assignment() -> None:
    """Unexpected body keys not on the allow-list are flagged for rejection."""
    requested = frozenset({"given_name", "staff_id", "is_admin"})
    allowed = frozenset({"given_name"})

    forbidden = forbidden_request_keys(requested, allowed)
    assert forbidden == frozenset({"staff_id", "is_admin"})


def test_forbidden_request_keys_empty_when_all_keys_allowed() -> None:
    """Exact allow-list match -> no forbidden keys."""
    keys = frozenset({"given_name", "staff_id"})
    assert forbidden_request_keys(keys, keys) == frozenset()
