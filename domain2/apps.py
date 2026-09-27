"""Asset models. Second schema, no edits to core/. Safe to delete."""

from django.apps import AppConfig


class Domain2Config(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "domain2"
