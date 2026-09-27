"""Test-only helpers for minting JWTs - synthetic keys only, not for production."""

from datetime import datetime
from typing import Any

from core.auth.local_tokens import mint_local_token


def mint_test_token(
    *,
    sub: str = "00000000-0000-4000-8000-000000000001",
    role: str = "colleague",
    exp: datetime | None = None,
    iss: str | None = None,
    aud: str | None = None,
    signing_key: str | None = None,
    extra_claims: dict[str, Any] | None = None,
    omit_claims: frozenset[str] = frozenset(),
) -> str:
    """Mint an HS256 JWT signed with the local test key for the test suite."""
    return mint_local_token(
        sub=sub,
        role=role,
        exp=exp,
        iss=iss,
        aud=aud,
        signing_key=signing_key,
        extra_claims=extra_claims,
        omit_claims=omit_claims,
    )
