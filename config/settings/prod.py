"""Production settings overlay - hardened HTTPS posture, Postgres via env.

    DJANGO_SETTINGS_MODULE=config.settings.prod gunicorn config.wsgi:application

Loads git-ignored .env.prod first (setdefault); shell exports still win.
Local dev, tests, and the cognito overlay never import this module.
"""

import os
from urllib.parse import unquote, urlparse

from django.core.exceptions import ImproperlyConfigured

from config.secrets import get_secret
from config.settings.cache_config import build_caches, is_shared_cache

from .env_utils import load_env_file

load_env_file(".env.prod")

from .base import *  # noqa: E402, F403


def _database_from_url(url: str) -> dict[str, str]:
    """Map a postgres:// URL to Django DATABASES['default'] - stdlib only."""
    parsed = urlparse(url)
    if parsed.scheme not in ("postgres", "postgresql"):
        msg = f"DATABASE_URL scheme must be postgres/postgresql, got {parsed.scheme!r}"
        raise ValueError(msg)
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": unquote(parsed.path.lstrip("/")),
        "USER": unquote(parsed.username or ""),
        "PASSWORD": unquote(parsed.password or ""),
        "HOST": parsed.hostname or "",
        "PORT": str(parsed.port or ""),
    }


DEBUG = False

# Fail closed: Django admin is a separate username/password surface Cognito does not
# protect - omit the app and URL in production.
ENABLE_DJANGO_ADMIN = False
INSTALLED_APPS = [  # noqa: F405
    app for app in INSTALLED_APPS if app != "django.contrib.admin"  # noqa: F405
]

# Fail closed: production must declare every host explicitly (no localhost default).
ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ["ALLOWED_HOSTS"].split(",")
    if host.strip()
]

# HTTPS / transport security - env-driven (HSTS seconds tunable without code changes).
SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "True").lower() in (
    "true",
    "1",
    "yes",
)
SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", "31536000"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_CONTENT_TYPE_NOSNIFF = True

# Production expects Postgres; SQLite stays the dev/test default in base/test.
# DATABASE_URL is resolved via config.secrets (env by default, optional SSM overlay).
# get_secret(required=True) already raised if missing; assert only narrows the type.
_database_url = get_secret("DATABASE_URL")
assert _database_url is not None  # nosec B101
DATABASES = {"default": _database_from_url(_database_url)}

# Collect static assets for a real server (collectstatic before gunicorn).
STATIC_ROOT = BASE_DIR / "staticfiles"  # noqa: F405

# Shared cache is mandatory in prod - LocMem throttle/dedup state is per-worker only.
_cache_url = get_secret("CACHE_URL", required=False) or get_secret(
    "REDIS_URL", required=False
)
CACHES = build_caches(cache_url=_cache_url)
if not is_shared_cache(CACHES):
    raise ImproperlyConfigured(
        "Production requires CACHE_URL or REDIS_URL for shared throttle counters "
        "and webhook idempotency across workers."
    )
