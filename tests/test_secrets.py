"""Secrets resolver - env backend and fail-closed behaviour."""

from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError
from config.secrets import SecretNotFoundError, get_secret


@pytest.fixture(autouse=True)
def _env_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    """Default path: env-only backend so the suite needs no AWS."""
    monkeypatch.setenv("SECRETS_BACKEND", "env")
    monkeypatch.delenv("TEST_SECRET_SAMPLE", raising=False)


def test_env_backend_returns_value_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Env backend reads the named variable from os.environ."""
    monkeypatch.setenv("TEST_SECRET_SAMPLE", "super-sensitive-value")
    assert get_secret("TEST_SECRET_SAMPLE") == "super-sensitive-value"


def test_env_backend_optional_missing_returns_none() -> None:
    """Optional secrets return None when absent - no exception."""
    assert get_secret("TEST_SECRET_SAMPLE", required=False) is None


def test_env_backend_required_missing_raises() -> None:
    """Required secrets fail closed when the variable is unset."""
    with pytest.raises(SecretNotFoundError, match="TEST_SECRET_SAMPLE"):
        get_secret("TEST_SECRET_SAMPLE")


def test_secret_value_never_in_error_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Threat: secret echoed in errors - message names the key only, never its value."""
    monkeypatch.setenv("OTHER_SECRET", "must-not-leak-in-error")
    with pytest.raises(SecretNotFoundError) as exc_info:
        get_secret("TEST_SECRET_SAMPLE")
    message = str(exc_info.value)
    assert message == "Required secret not found: TEST_SECRET_SAMPLE"
    assert "must-not-leak-in-error" not in message


def test_env_backend_empty_string_treated_as_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Empty env values are not valid secrets - same as unset for required keys."""
    monkeypatch.setenv("TEST_SECRET_SAMPLE", "")
    with pytest.raises(SecretNotFoundError):
        get_secret("TEST_SECRET_SAMPLE")


def test_secrets_backend_defaults_to_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unset SECRETS_BACKEND must stay env so CI needs no cloud flag."""
    monkeypatch.delenv("SECRETS_BACKEND", raising=False)
    monkeypatch.setenv("TEST_SECRET_SAMPLE", "from-default-env-backend")
    assert get_secret("TEST_SECRET_SAMPLE") == "from-default-env-backend"


def test_invalid_secrets_backend_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unknown backend values fail closed at resolution time."""
    monkeypatch.setenv("SECRETS_BACKEND", "vault")
    with pytest.raises(ValueError, match="SECRETS_BACKEND"):
        get_secret("ANY_KEY")


@pytest.fixture
def aws_backend(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Switch to aws backend with a mocked SSM client - no cloud in CI."""
    monkeypatch.setenv("SECRETS_BACKEND", "aws")
    client = MagicMock()
    monkeypatch.setattr("config.secrets._ssm_client", lambda: client)
    return client


def test_aws_backend_returns_value_from_ssm(aws_backend: MagicMock) -> None:
    """AWS backend reads the named SSM parameter (decrypted SecureString)."""
    aws_backend.get_parameter.return_value = {
        "Parameter": {"Value": "db-password-from-ssm"},
    }
    assert get_secret("/myapp/prod/DATABASE_PASSWORD") == "db-password-from-ssm"
    aws_backend.get_parameter.assert_called_once_with(
        Name="/myapp/prod/DATABASE_PASSWORD",
        WithDecryption=True,
    )


def test_aws_backend_required_missing_raises(aws_backend: MagicMock) -> None:
    """Missing SSM parameters fail closed for required secrets."""
    aws_backend.get_parameter.side_effect = ClientError(
        {"Error": {"Code": "ParameterNotFound", "Message": "not found"}},
        "GetParameter",
    )
    with pytest.raises(SecretNotFoundError, match="/myapp/prod/MISSING"):
        get_secret("/myapp/prod/MISSING")


def test_aws_backend_secret_value_never_in_error_message(
    aws_backend: MagicMock,
) -> None:
    """Threat: SSM value echoed in errors - message names the key only."""
    aws_backend.get_parameter.side_effect = ClientError(
        {"Error": {"Code": "ParameterNotFound", "Message": "not found"}},
        "GetParameter",
    )
    with pytest.raises(SecretNotFoundError) as exc_info:
        get_secret("/myapp/prod/OTHER")
    message = str(exc_info.value)
    assert message == "Required secret not found: /myapp/prod/OTHER"
    assert "db-password-from-ssm" not in message


def test_aws_backend_empty_string_treated_as_missing(
    aws_backend: MagicMock,
) -> None:
    """Empty SSM values are not valid secrets - same as unset for required keys."""
    aws_backend.get_parameter.return_value = {"Parameter": {"Value": ""}}
    with pytest.raises(SecretNotFoundError):
        get_secret("/myapp/prod/EMPTY")
