"""Cognito overlay - everything from dev, plus the git-ignored .env.cognito.

    python manage.py runserver --settings=config.settings.cognito
    DJANGO_SETTINGS_MODULE=config.settings.cognito python manage.py seed

Local dev (HS256) and the test suite are untouched - they never import this
module. .env.cognito is loaded before dev/base read the environment, and uses
setdefault, so shell exports still override it.
"""

from .env_utils import load_env_file

load_env_file(".env.cognito")

from .dev import *  # noqa: E402, F403
