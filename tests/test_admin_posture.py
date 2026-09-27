"""Django admin exposure - enabled in dev/test, omitted in prod."""

from django.test import Client


def test_admin_route_available_in_test_settings() -> None:
    """Dev/test keep /admin/ for local inspection - must not 404."""
    response = Client().get("/admin/")
    assert response.status_code != 404


def test_prod_admin_route_returns_404() -> None:
    """Prod must not register /admin/ - separate credential surface."""
    import os
    import subprocess
    import sys
    import textwrap

    env = os.environ.copy()
    env.update(
        {
            "SECRET_KEY": "test-only-not-for-production",
            "ALLOWED_HOSTS": "example.com",
            "DATABASE_URL": "postgresql://user:pass@localhost:5432/mydb",
            "CACHE_URL": "redis://127.0.0.1:6379/0",
            "SECURE_SSL_REDIRECT": "False",
            "DJANGO_SETTINGS_MODULE": "config.settings.prod",
        }
    )
    script = textwrap.dedent(
        """
        import django

        django.setup()
        from django.test import Client

        response = Client(HTTP_HOST="example.com").get("/admin/")
        assert response.status_code == 404
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
