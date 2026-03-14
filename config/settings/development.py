"""
config/settings/development.py

Local development settings.
  - DEBUG=True
  - SQLite or local Postgres
  - All origins allowed for CORS (localhost)
  - Django Debug Toolbar ready
  - Logs to console at DEBUG level
  - Celery tasks run eagerly (no broker needed)

Usage:
    DJANGO_SETTINGS_MODULE=config.settings.development python manage.py runserver
"""
from __future__ import annotations

import os

from .base import *  # noqa: F401, F403

# ── Debug ──────────────────────────────────────────────────────────────────────
DEBUG = True

SECRET_KEY = os.getenv(  # type: ignore[assignment]
    "SECRET_KEY",
    "django-insecure-dev-only-do-not-use-in-production-1234567890abcdef"
)

ALLOWED_HOSTS = ["*"]

# ── CORS — allow all origins in development ────────────────────────────────────
CORS_ALLOW_ALL_ORIGINS = True

# ── Email — print to console in dev ───────────────────────────────────────────
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# ── Celery — run tasks synchronously (no Redis/broker needed locally) ──────────
# Remove these lines if you want to test actual async tasks during development
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# ── Cache — use local memory cache so dev works without Redis ─────────────────
# Comment this out if you have Redis running locally
CACHES = {  # type: ignore[assignment]
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "buddy-dev-cache",
    }
}

# ── Channels — use in-memory layer so dev works without Redis ──────────────────
# Comment this out if you want to test actual horizontal scaling with Redis
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    },
}

# ── Logging — verbose debug output to console ─────────────────────────────────
LOGGING = {  # type: ignore[assignment]
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "colored": {
            "format": "\033[36m[{asctime}]\033[0m \033[1m{levelname:<8}\033[0m {name}: {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "colored",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "DEBUG",
    },
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "django.db.backends": {
            # Uncomment to see every SQL query in the console:
            # "level": "DEBUG",
            "level": "WARNING",
            "handlers": ["console"],
            "propagate": False,
        },
        "api": {"handlers": ["console"], "level": "DEBUG", "propagate": False},
        "apps": {"handlers": ["console"], "level": "DEBUG", "propagate": False},
    },
}

# ── Django Debug Toolbar (install separately: pip install django-debug-toolbar) ─
# Uncomment if you install django-debug-toolbar
# INSTALLED_APPS += ["debug_toolbar"]
# MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")
# INTERNAL_IPS = ["127.0.0.1"]
