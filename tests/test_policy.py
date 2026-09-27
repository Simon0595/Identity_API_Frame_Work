"""Policy tests. Missing rows mean no access."""

from core.policy import resolve_readable_visibilities, resolve_writable_visibilities


class _StubReadableLookup:
    """In-memory readable policy rows for unit tests - no ORM."""

    def __init__(self, rows: dict[tuple[str, str], list[str]]) -> None:
        self._rows = rows

    def readable_visibilities_for(self, role: str, context: str) -> list[str] | None:
        return self._rows.get((role, context))


class _StubWritableLookup:
    """In-memory writable policy rows for unit tests - no ORM."""

    def __init__(self, rows: dict[tuple[str, str], list[str]]) -> None:
        self._rows = rows

    def writable_visibilities_for(self, role: str, context: str) -> list[str] | None:
        return self._rows.get((role, context))


def test_resolve_readable_visibilities_returns_stored_set() -> None:
    """Happy path: exact visibility classes for a known (role, context) pair."""
    lookup = _StubReadableLookup(
        {
            ("colleague", "professional"): ["public", "restricted"],
        }
    )
    result = resolve_readable_visibilities("colleague", "professional", lookup)
    assert result == frozenset({"public", "restricted"})


def test_resolve_readable_visibilities_missing_policy_denies_by_default() -> None:
    """No policy row -> empty set so downstream redaction yields nothing readable."""
    lookup = _StubReadableLookup({})
    result = resolve_readable_visibilities("colleague", "professional", lookup)
    assert result == frozenset()


def test_resolve_readable_visibilities_empty_list_denies_by_default() -> None:
    """Empty readable list is denial - caller may see nothing (404 later)."""
    lookup = _StubReadableLookup({("public_caller", "personal"): []})
    result = resolve_readable_visibilities("public_caller", "personal", lookup)
    assert result == frozenset()


def test_resolve_readable_visibilities_rejects_blank_lookup_keys() -> None:
    """Blank role or context is ambiguous - deny rather than guess."""
    lookup = _StubReadableLookup({("colleague", "professional"): ["public"]})
    assert resolve_readable_visibilities("", "professional", lookup) == frozenset()
    assert resolve_readable_visibilities("colleague", "", lookup) == frozenset()


def test_resolve_writable_visibilities_returns_stored_set() -> None:
    """Happy path: exact writable classes for a known (role, context) pair."""
    lookup = _StubWritableLookup(
        {
            ("subject", "personal"): ["public", "restricted"],
        }
    )
    result = resolve_writable_visibilities("subject", "personal", lookup)
    assert result == frozenset({"public", "restricted"})


def test_resolve_writable_visibilities_missing_policy_denies_by_default() -> None:
    """No policy row -> empty writable set so write path denies (403 + audit)."""
    lookup = _StubWritableLookup({})
    result = resolve_writable_visibilities("colleague", "professional", lookup)
    assert result == frozenset()


def test_resolve_writable_visibilities_empty_list_denies_by_default() -> None:
    """Empty writable list is denial - unauthorised write, nothing persisted."""
    lookup = _StubWritableLookup({("public_caller", "professional"): []})
    result = resolve_writable_visibilities("public_caller", "professional", lookup)
    assert result == frozenset()


def test_resolve_writable_visibilities_rejects_blank_lookup_keys() -> None:
    """Blank role or context is ambiguous - deny rather than guess."""
    lookup = _StubWritableLookup({("subject", "personal"): ["public"]})
    assert resolve_writable_visibilities("", "personal", lookup) == frozenset()
    assert resolve_writable_visibilities("subject", "", lookup) == frozenset()
