"""
WSGI config for deployment. Uses dev settings unless the host sets
DJANGO_SETTINGS_MODULE (production should set it explicitly).
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

application = get_wsgi_application()
