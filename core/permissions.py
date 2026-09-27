"""Which keys a caller may write. Extra keys are rejected."""

from collections.abc import Iterable
from typing import Protocol


class WritableField(Protocol):
    """domain rows expose key and visibility."""

    @property
    def key(self) -> str: ...

    @property
    def visibility(self) -> str: ...


def allowed_write_keys(
    fields: Iterable[WritableField],
    writable_visibilities: frozenset[str],
) -> frozenset[str]:
    """
    Return profile-field keys the caller may write for this (role, context).

    Deny by default: empty writable set or visibility not in the set -> key omitted.
    """
    if not writable_visibilities:
        return frozenset()

    return frozenset(
        field.key for field in fields if field.visibility in writable_visibilities
    )


def forbidden_request_keys(
    requested_keys: frozenset[str],
    allowed_keys: frozenset[str],
) -> frozenset[str]:
    """
    Keys in the request body that are not on the writable allow-list.

    Non-empty result means mass-assignment or unauthorised field - reject the write.
    """
    return requested_keys - allowed_keys
