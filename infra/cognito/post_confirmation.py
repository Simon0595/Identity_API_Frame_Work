"""Cognito post-confirmation Lambda. New sign-ups join a default group.

The group is set here, not by the client. Only real self-service sign-up
confirmations get a group; other trigger sources are ignored.
"""

from __future__ import annotations

import os
from typing import Any

# Cognito reuses this trigger for several flows; only auto-assign on a real
# self-service sign-up confirmation - never for admin-created users, external IdP
# links, or forgot-password confirmations.
_CONFIRM_SIGNUP_SOURCE = "PostConfirmation_ConfirmSignUp"

# Least-privilege default. Must name an existing Cognito group whose name
# matches a role string the API maps (see ROLE_PRECEDENCE in core/auth/cognito.py).
DEFAULT_GROUP = "public_caller"


def default_group() -> str:
    """Group new sign-ups join. DEFAULT_SIGNUP_GROUP env lets a consumer override
    the baseline without editing code; blank/unset falls back to least privilege."""
    return os.getenv("DEFAULT_SIGNUP_GROUP", "").strip() or DEFAULT_GROUP


def should_assign_group(event: dict[str, Any]) -> bool:
    """True only for genuine self-service sign-up confirmations (deny by default)."""
    return event.get("triggerSource") == _CONFIRM_SIGNUP_SOURCE


def _cognito_client() -> Any:
    """Return a Cognito IDP client via the Lambda's execution role.

    Separated so tests inject a mock without boto3, credentials, or network.
    """
    import boto3

    return boto3.client("cognito-idp")


def handler(event: dict[str, Any], _context: Any = None) -> dict[str, Any]:
    """Post-confirmation entry point: add confirmed sign-ups to the default group.

    Cognito requires the original event returned unchanged; non-signup triggers
    pass through untouched. Assumes the Lambda execution role holds
    cognito-idp:AdminAddUserToGroup on this user pool (see the SAM template).
    """
    if should_assign_group(event):
        _cognito_client().admin_add_user_to_group(
            UserPoolId=event["userPoolId"],
            Username=event["userName"],
            GroupName=default_group(),
        )
    return event
