"""Runtime secret resolution - env-first, optional AWS overlay."""

import os
from typing import Any, Literal

SecretBackend = Literal["env", "aws"]


class SecretNotFoundError(LookupError):
    """Required secret missing - message names the key only, never the value."""


def _backend() -> SecretBackend:
    """Return the configured backend; invalid values fail closed at startup."""
    raw = os.getenv("SECRETS_BACKEND", "env").lower()
    if raw not in ("env", "aws"):
        msg = f"SECRETS_BACKEND must be 'env' or 'aws', got {raw!r}"
        raise ValueError(msg)
    return raw  # type: ignore[return-value]


def get_secret(name: str, *, required: bool = True) -> str | None:
    """Return secret name from the configured backend.

    When required is True (default), raises SecretNotFoundError if absent
    or empty. Optional secrets return None when missing. Errors never echo
    secret values.
    """
    backend = _backend()
    if backend == "env":
        value = os.getenv(name)
    else:
        value = _get_from_aws(name)

    if not value:
        if required:
            raise SecretNotFoundError(f"Required secret not found: {name}")
        return None
    return value


def _ssm_client() -> Any:
    """Return an SSM client via the default credential chain (instance/task role).

    Separated so tests can inject a mock without network or installed boto3 on the
    default env path.
    """
    import boto3

    return boto3.client("ssm")


def _get_from_aws(name: str) -> str | None:
    """Fetch name from SSM Parameter Store (SecureString, decrypted).

    Uses ambient IAM role credentials - never long-lived access keys on the box.
    name is the full parameter path (e.g. /myapp/prod/DATABASE_PASSWORD).
    """
    from botocore.exceptions import ClientError

    client = _ssm_client()
    try:
        response = client.get_parameter(Name=name, WithDecryption=True)
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        if code == "ParameterNotFound":
            return None
        msg = f"Failed to fetch secret from AWS SSM: {name}"
        raise RuntimeError(msg) from None

    return str(response["Parameter"]["Value"])
