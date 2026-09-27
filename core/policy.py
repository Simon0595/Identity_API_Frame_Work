"""Which visibility classes a role may read or write in a given context.

Works on class names only, not field names. Missing policy means no access.
"""

from typing import Protocol


class ReadablePolicyLookup(Protocol):
    """domain supplies ORM-backed lookup in the DRF view layer."""

    def readable_visibilities_for(self, role: str, context: str) -> list[str] | None:
        """Return visibility class strings, or None when no policy row exists."""


class WritablePolicyLookup(Protocol):
    """domain supplies ORM-backed writable lookup in the view layer."""

    def writable_visibilities_for(self, role: str, context: str) -> list[str] | None:
        """Return writable visibility classes, or None when no policy row exists."""


def _resolve_visibilities(
    role: str,
    context: str,
    visibilities: list[str] | None,
) -> frozenset[str]:
    """Shared deny-by-default path for readable and writable resolution."""
    if not role or not context:
        return frozenset()
    if visibilities is None:
        return frozenset()
    return frozenset(visibilities)


def resolve_readable_visibilities(
    role: str,
    context: str,
    lookup: ReadablePolicyLookup,
) -> frozenset[str]:
    """
    Readable visibility classes for (role, context).

    context is lookup input only - this function never widens visibility beyond
    what storage returns for that exact pair.
    """
    return _resolve_visibilities(
        role,
        context,
        lookup.readable_visibilities_for(role, context),
    )


def resolve_writable_visibilities(
    role: str,
    context: str,
    lookup: WritablePolicyLookup,
) -> frozenset[str]:
    """
    Writable visibility classes for (role, context).

    Used by the write path to allow-list profile fields by visibility class only.
    Missing policy or empty list -> deny (403 + audit denied).
    """
    return _resolve_visibilities(
        role,
        context,
        lookup.writable_visibilities_for(role, context),
    )
