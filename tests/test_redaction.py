"""Redaction tests. Unknown classes are dropped."""

from dataclasses import dataclass

from core.redaction import redact_by_visibility


@dataclass(frozen=True)
class _StubField:
    """Synthetic field record - visibility class only, no domain field names."""

    visibility: str


def test_redact_keeps_fields_in_readable_set() -> None:
    """Happy path: permitted visibility classes survive redaction."""
    fields = [
        _StubField("public"),
        _StubField("restricted"),
        _StubField("confidential"),
    ]
    readable = frozenset({"public", "restricted"})

    result = redact_by_visibility(fields, readable)

    assert [f.visibility for f in result] == ["public", "restricted"]


def test_redact_empty_readable_set_denies_all() -> None:
    """No readable visibilities -> nothing disclosed (downstream maps to 404)."""
    fields = [_StubField("public")]
    assert redact_by_visibility(fields, frozenset()) == []


def test_redact_excludes_unlisted_visibility() -> None:
    """Confidential (or any class not in policy) never passes redaction."""
    fields = [
        _StubField("public"),
        _StubField("confidential"),
    ]
    readable = frozenset({"public"})

    result = redact_by_visibility(fields, readable)

    assert len(result) == 1
    assert result[0].visibility == "public"
