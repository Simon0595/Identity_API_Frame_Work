"""Local HS256 token minting - shared by tests and the guarded dev-login endpoint."""

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from django.conf import settings


def mint_local_token(
    *,
    sub: str,
    role: str,
    exp: datetime | None = None,
    iss: str | None = None,
    aud: str | None = None,
    signing_key: str | None = None,
    extra_claims: dict[str, Any] | None = None,
    omit_claims: frozenset[str] = frozenset(),
) -> str:
    """Mint an HS256 JWT using local issuer settings (dev/test only)."""
    now = datetime.now(tz=UTC)
    payload: dict[str, Any] = {
        "sub": sub,
        "role": role,
        "iss": iss if iss is not None else settings.AUTH_LOCAL_ISSUER,
        "aud": aud if aud is not None else settings.AUTH_LOCAL_AUDIENCE,
        "exp": exp if exp is not None else now + timedelta(hours=1),
        "iat": now,
    }
    if extra_claims:
        payload.update(extra_claims)
    for claim in omit_claims:
        payload.pop(claim, None)

    key = signing_key if signing_key is not None else settings.AUTH_LOCAL_SIGNING_KEY
    return jwt.encode(payload, key, algorithm="HS256")


def dev_login_enabled() -> bool:
    """True only when offline HS256 dev login is explicitly allowed - never in prod."""
    return settings.AUTH_ISSUER == "local" and settings.DEBUG
