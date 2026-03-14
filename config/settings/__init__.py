"""
config/settings/__init__.py

Auto-selects the correct settings module based on the DJANGO_ENV environment
variable. Falls back to development if not set.

    DJANGO_ENV=development  →  config.settings.development
    DJANGO_ENV=production   →  config.settings.production
    DJANGO_ENV=test         →  config.settings.development  (same as dev)

This file makes `config.settings` itself importable as a settings module,
so existing DJANGO_SETTINGS_MODULE=config.settings still works.
"""
import os

_env = os.getenv("DJANGO_ENV", "development").lower()

if _env == "production":
    from .production import *  # noqa: F401, F403
else:
    from .development import *  # noqa: F401, F403
