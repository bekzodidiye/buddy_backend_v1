"""
config/settings/production.py

Production settings — security hardened, performance optimized.

Required environment variables (set in your hosting platform):
    SECRET_KEY           — Django secret key (long random string)
    DATABASE_URL         — PostgreSQL connection string
    REDIS_URL            — Redis connection string
    ALLOWED_HOSTS        — Comma-separated list of allowed hostnames
    DJANGO_LOG_LEVEL     — (optional) Log level, default INFO

Usage:
    DJANGO_SETTINGS_MODULE=config.settings.production gunicorn config.wsgi
"""
from __future__ import annotations

import os

from .base import *  # noqa: F401, F403

# ── Security ───────────────────────────────────────────────────────────────────
DEBUG = False

# Enforce HTTPS
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000          # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Cookie security
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Strict"

# Browser security headers
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# ── CORS — explicit whitelist only in production ───────────────────────────────
# CORS_ALLOW_ALL_ORIGINS is NOT set here — base.py's CORS_ALLOWED_ORIGINS applies.
# To add new origins, update CORS_ALLOWED_ORIGINS in base.py or via env:
_extra_origins = os.getenv("EXTRA_CORS_ORIGINS", "")
if _extra_origins:
    CORS_ALLOWED_ORIGINS = list(CORS_ALLOWED_ORIGINS) + [  # type: ignore[name-defined]
        o.strip() for o in _extra_origins.split(",") if o.strip()
    ]

# ── Email ──────────────────────────────────────────────────────────────────────
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER)
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# ── Admins — receive 500 error emails ─────────────────────────────────────────
_admin_emails = os.getenv("DJANGO_ADMINS", "")
if _admin_emails:
    ADMINS = [
        (name.strip(), email.strip())
        for pair in _admin_emails.split(";")
        if ":" in pair
        for name, email in [pair.split(":", 1)]
    ]

# ── Logging ────────────────────────────────────────────────────────────────────
LOGGING = {  # type: ignore[assignment]
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter"
            if os.getenv("LOG_FORMAT") == "json"
            else "logging.Formatter",
            "format": "[{asctime}] {levelname} {name} {message}",
            "style": "{",
        },
        "verbose": {
            "format": "[{asctime}] {levelname} {name} pid={process} {message}",
            "style": "{",
        },
    },
    "filters": {
        "require_debug_false": {
            "()": "django.utils.log.RequireDebugFalse",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "mail_admins": {
            "level": "ERROR",
            "class": "django.utils.log.AdminEmailHandler",
            "filters": ["require_debug_false"],
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": os.getenv("DJANGO_LOG_LEVEL", "INFO"),
            "propagate": False,
        },
        "django.security": {
            "handlers": ["console", "mail_admins"],
            "level": "ERROR",
            "propagate": False,
        },
        "api": {
            "handlers": ["console"],
            "level": os.getenv("DJANGO_LOG_LEVEL", "INFO"),
            "propagate": False,
        },
        "apps": {
            "handlers": ["console"],
            "level": os.getenv("DJANGO_LOG_LEVEL", "INFO"),
            "propagate": False,
        },
        "celery": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "urllib3": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}
