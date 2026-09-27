"""AWS Cognito TokenVerifier - RS256 via cached JWKS, groups mapped to app roles."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

import jwt
from django.conf import settings
from jwt.algorithms import RSAAlgorithm

from core.auth.verifier import TokenValidationError

# Explicit allow-list - rejects alg=none and HS/RS confusion.
ALLOWED_ALGORITHMS: tuple[str, ...] = ("RS256",)

# When a token carries multiple Cognito groups, pick the highest-privilege app role.
ROLE_PRECEDENCE: tuple[str, ...] = ("admin", "colleague", "subject", "public_caller")

JwksFetcher = Callable[[str], dict[str, Any]]


def _default_fetch_jwks(url: str) -> dict[str, Any]:
    """Fetch JWKS from Cognito - production path only; tests replace this."""
    if not url.startswith("https://"):
        # JWKS must be https so a bad COGNITO_JWKS_URL cannot read local files.
        raise TokenValidationError("JWKS URL must be https")
    try:
        with urlopen(url, timeout=10) as response:  # nosec B310
            payload: dict[str, Any] = json.loads(response.read())
            return payload
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise TokenValidationError("Unable to fetch JWKS") from exc


class JwksCache:
    """In-memory JWKS keyed by kid; refresh once when an unknown kid appears."""

    def __init__(
        self,
        jwks_url: str,
        *,
        fetch_jwks: JwksFetcher | None = None,
    ) -> None:
        self._url = jwks_url
        self._fetch = fetch_jwks or _default_fetch_jwks
        self._keys_by_kid: dict[str, Any] = {}

    def get_signing_key(self, kid: str) -> Any:
        """Return the RSA public key for kid, refreshing JWKS once if missing."""
        if kid not in self._keys_by_kid:
            self._refresh()
        if kid not in self._keys_by_kid:
            raise TokenValidationError(f"Unknown signing key: {kid}")
        return self._keys_by_kid[kid]

    def _refresh(self) -> None:
        jwks = self._fetch(self._url)
        keys = jwks.get("keys")
        if not isinstance(keys, list):
            raise TokenValidationError("Invalid JWKS payload")
        self._keys_by_kid = {
            entry["kid"]: RSAAlgorithm.from_jwk(json.dumps(entry))
            for entry in keys
            if isinstance(entry, dict) and "kid" in entry
        }


def map_cognito_groups_to_role(groups: object) -> str:
    """Map cognito:groups claim values to a single app role string."""
    if not isinstance(groups, list) or not groups:
        raise TokenValidationError("Token missing Cognito groups for role mapping")
    group_set = {g for g in groups if isinstance(g, str)}
    for role in ROLE_PRECEDENCE:
        if role in group_set:
            return role
    raise TokenValidationError("No Cognito group maps to an app role")


class CognitoTokenVerifier:
    """Verify Cognito-issued RS256 JWTs using cached pool JWKS."""

    def __init__(
        self,
        *,
        fetch_jwks: JwksFetcher | None = None,
        jwks_cache: JwksCache | None = None,
    ) -> None:
        jwks_url = settings.COGNITO_JWKS_URL
        self._cache = jwks_cache or JwksCache(jwks_url, fetch_jwks=fetch_jwks)
        self._issuer = settings.COGNITO_ISSUER
        self._client_id = settings.COGNITO_APP_CLIENT_ID

    def verify(self, token: str) -> dict[str, Any]:
        try:
            header = jwt.get_unverified_header(token)
        except jwt.InvalidTokenError as exc:
            raise TokenValidationError(str(exc)) from exc

        alg = header.get("alg")
        if alg not in ALLOWED_ALGORITHMS:
            raise TokenValidationError(f"Algorithm not allowed: {alg!r}")

        kid = header.get("kid")
        if not isinstance(kid, str) or not kid:
            raise TokenValidationError("Token missing kid")

        signing_key = self._cache.get_signing_key(kid)

        try:
            # leeway: tolerate small clock skew between this host and Cognito.
            # Without it, a Mac a few dozen seconds behind AWS rejects freshly
            # minted tokens with "The token is not yet valid (iat)" -> opaque 401.
            claims: dict[str, Any] = jwt.decode(
                token,
                signing_key,
                algorithms=list(ALLOWED_ALGORITHMS),
                issuer=self._issuer,
                leeway=60,
                options={
                    "require": ["exp", "iss", "sub"],
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_nbf": True,
                    "verify_aud": False,
                },
            )
        except jwt.InvalidTokenError as exc:
            raise TokenValidationError(str(exc)) from exc

        audience = claims.get("aud") or claims.get("client_id")
        if audience != self._client_id:
            raise TokenValidationError("Invalid audience")

        role = map_cognito_groups_to_role(claims.get("cognito:groups"))
        return {**claims, "role": role}
