"""Local development settings - DEBUG on, inherits everything else from base.

Loads the project-root .env so cp.env.example.env is enough for
manage.py; explicit shell exports still win (see env_utils.load_env_file).
Defaults to the local HS256 issuer - use config.settings.cognito to run
against a real Cognito pool without exporting vars by hand.
"""

import os

from .env_utils import load_env_file

load_env_file(".env")

from .base import *  # noqa: E402, F403

DEBUG = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")
