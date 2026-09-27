"""Drop fields the caller is not allowed to see."""

from collections.abc import Iterable
from typing import Protocol


class VisibilityTagged(Protocol):
    """domain ProfileField rows satisfy this via visibility."""

    @property
    def visibility(self) -> str: ...


def redact_by_visibility(
    fields: Iterable[VisibilityTagged],
    readable_visibilities: frozenset[str],
) -> list[VisibilityTagged]:
    """
    Return only fields whose visibility class is permitted for the caller.

    Deny by default: empty readable set, or visibility not in the set, is dropped.
    """
    if not readable_visibilities:
        return []

    return [
        field
        for field in fields
        if field.visibility in readable_visibilities
    ]
