"""
Test settings - in-memory DB and fast hashers keep pytest runs quick.
pytest picks this module via pyproject.toml (not manage.py).
"""

import os

# Tests must not depend on a developer .env; base.py requires SECRET_KEY at import.
os.environ.setdefault("SECRET_KEY", "test-only-not-for-production")

from .base import *  # noqa: F403

# Always use the local HS256 issuer here, even if the shell still has
# AUTH_ISSUER=cognito from a live pool.
AUTH_ISSUER = "local"

DEBUG = False

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]
