"""Production settings overlay - hardening flags without a live Postgres connection."""

import os
import subprocess
import sys
import textwrap


def _run_prod_import_assertions(
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Import config.settings.prod in an isolated interpreter and assert flags."""
    env = os.environ.copy()
    env.update(
        {
            "SECRET_KEY": "test-only-not-for-production",
            "ALLOWED_HOSTS": "example.com,api.example.com",
            "DATABASE_URL": "postgresql://dbuser:secret%40pass@db.example.com:5432/mydb",
            "CACHE_URL": "redis://cache.example.com:6379/0",
            "SECURE_SSL_REDIRECT": "True",
            "SECURE_HSTS_SECONDS": "31536000",
        }
    )
    if extra_env:
        env.update(extra_env)
    script = textwrap.dedent(
        """
        import config.settings.prod as prod

        assert prod.DEBUG is False
        assert prod.ENABLE_DJANGO_ADMIN is False
        assert "django.contrib.admin" not in prod.INSTALLED_APPS
        assert prod.ALLOWED_HOSTS == ["example.com", "api.example.com"]
        assert prod.SECURE_SSL_REDIRECT is True
        assert prod.SECURE_HSTS_SECONDS == 31536000
        assert prod.SECURE_HSTS_INCLUDE_SUBDOMAINS is True
        assert prod.SECURE_HSTS_PRELOAD is True
        assert prod.SESSION_COOKIE_SECURE is True
        assert prod.CSRF_COOKIE_SECURE is True
        assert prod.SECURE_PROXY_SSL_HEADER == ("HTTP_X_FORWARDED_PROTO", "https")
        assert prod.SECURE_CONTENT_TYPE_NOSNIFF is True
        db = prod.DATABASES["default"]
        assert db["ENGINE"] == "django.db.backends.postgresql"
        assert db["NAME"] == "mydb"
        assert db["USER"] == "dbuser"
        assert db["PASSWORD"] == "secret@pass"
        assert db["HOST"] == "db.example.com"
        assert db["PORT"] == "5432"
        cache = prod.CACHES["default"]
        assert cache["BACKEND"] == "django.core.cache.backends.redis.RedisCache"
        assert cache["LOCATION"] == "redis://cache.example.com:6379/0"
        """
    )
    return subprocess.run(
        [sys.executable, "-c", script],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_prod_overlay_sets_debug_false_and_secure_flags() -> None:
    """Prod overlay must fail closed on DEBUG and HTTPS posture when env is set."""
    result = _run_prod_import_assertions()
    assert result.returncode == 0, result.stderr or result.stdout


def test_prod_deploy_check_reports_no_security_warnings() -> None:
    """check --deploy must be clean when prod env is set (no live DB needed)."""
    env = os.environ.copy()
    env.update(
        {
            # Django W009 fires on short/test keys - use a long random value in prod.
            "SECRET_KEY": "prod-check-test-" + "a" * 50,
            "ALLOWED_HOSTS": "example.com",
            "DATABASE_URL": "postgresql://user:pass@localhost:5432/mydb",
            "CACHE_URL": "redis://127.0.0.1:6379/0",
            "SECURE_SSL_REDIRECT": "True",
            "SECURE_HSTS_SECONDS": "31536000",
            "DJANGO_SETTINGS_MODULE": "config.settings.prod",
        }
    )
    result = subprocess.run(
        [sys.executable, "manage.py", "check", "--deploy"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    combined = (result.stdout + result.stderr).lower()
    assert result.returncode == 0, result.stderr or result.stdout
    assert "no issues" in combined
    assert "warnings:" not in combined


def test_prod_overlay_rejects_non_postgres_database_url() -> None:
    """DATABASE_URL must be postgres - sqlite in production is a misconfiguration."""
    env = os.environ.copy()
    env.update(
        {
            "SECRET_KEY": "test-only-not-for-production",
            "ALLOWED_HOSTS": "example.com",
            "DATABASE_URL": "sqlite:///tmp/wrong.db",
        }
    )
    script = textwrap.dedent(
        """
        try:
            import config.settings.prod # noqa: F401
        except ValueError as exc:
            assert "postgres" in str(exc)
        else:
            raise AssertionError("expected ValueError for non-postgres DATABASE_URL")
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
