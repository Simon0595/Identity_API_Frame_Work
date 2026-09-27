"""Cognito post-confirmation Lambda - default-group assignment (optional infra)."""

from typing import Any
from unittest.mock import MagicMock

import pytest
from infra.cognito import post_confirmation as pc


@pytest.fixture
def cognito(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Mocked Cognito IDP client so no admin call ever leaves the test."""
    client = MagicMock()
    monkeypatch.setattr(pc, "_cognito_client", lambda: client)
    return client


def _signup_event() -> dict[str, Any]:
    return {
        "triggerSource": "PostConfirmation_ConfirmSignUp",
        "userPoolId": "eu-west-1_example",
        "userName": "new-user",
    }


def test_confirmed_signup_added_to_default_group(cognito: MagicMock) -> None:
    """A genuine sign-up confirmation joins the least-privilege default group."""
    event = _signup_event()
    result = pc.handler(event)

    cognito.admin_add_user_to_group.assert_called_once_with(
        UserPoolId="eu-west-1_example",
        Username="new-user",
        GroupName="public_caller",
    )
    # Cognito requires the event returned unchanged.
    assert result is event


def test_default_group_env_override(
    cognito: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Consumers can change the baseline group via env without editing code."""
    monkeypatch.setenv("DEFAULT_SIGNUP_GROUP", "subject")
    pc.handler(_signup_event())
    _, kwargs = cognito.admin_add_user_to_group.call_args
    assert kwargs["GroupName"] == "subject"


def test_blank_override_falls_back_to_least_privilege(
    cognito: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A blank override must not disable the default - fall back to public_caller."""
    monkeypatch.setenv("DEFAULT_SIGNUP_GROUP", "   ")
    assert pc.default_group() == "public_caller"


@pytest.mark.parametrize(
    "trigger",
    [
        "PostConfirmation_ConfirmForgotPassword",
        "PreSignUp_AdminCreateUser",
        "PostAuthentication_Authentication",
        "",
    ],
)
def test_non_signup_triggers_assign_nothing(cognito: MagicMock, trigger: str) -> None:
    """Deny by default: only real sign-up confirmations grant a group."""
    event = {**_signup_event(), "triggerSource": trigger}
    result = pc.handler(event)
    cognito.admin_add_user_to_group.assert_not_called()
    assert result is event


def test_missing_trigger_source_assigns_nothing(cognito: MagicMock) -> None:
    """A malformed event without triggerSource must not grant privilege."""
    pc.handler({"userPoolId": "p", "userName": "u"})
    cognito.admin_add_user_to_group.assert_not_called()
