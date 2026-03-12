"""
Token Blacklist Service — Redis yordamida.

Har bir logout bo'lganda yoki token rotate bo'lganda,
eski refresh token Redis ga qo'shiladi va token muddati
tugagüncha unda saqlanib turadi.

Bu replay attack lardan himoya qiladi.
"""
import hashlib
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache

# Redis key prefix
BLACKLIST_PREFIX = "token_blacklist:"
# Fallback — Redis yo'q bo'lsa, in-memory (development uchun)
_memory_blacklist: set = set()


def _get_token_hash(token: str) -> str:
    """Token ni SHA-256 bilan hash qilib, Redis key yaratadi."""
    return hashlib.sha256(token.encode()).hexdigest()


def blacklist_token(token: str, lifetime_seconds: int | None = None) -> None:
    """
    Refresh tokenni blacklist ga qo'shadi.

    Args:
        token: Refresh token string
        lifetime_seconds: Tokenning qancha vaqt Redis da saqlanishi (default: REFRESH_TOKEN_LIFETIME)
    """
    if lifetime_seconds is None:
        refresh_lifetime: timedelta = settings.SIMPLE_JWT.get(
            'REFRESH_TOKEN_LIFETIME', timedelta(days=7)
        )
        lifetime_seconds = int(refresh_lifetime.total_seconds())

    token_hash = _get_token_hash(token)
    key = f"{BLACKLIST_PREFIX}{token_hash}"

    try:
        cache.set(key, "1", timeout=lifetime_seconds)
    except Exception:
        # Redis mavjud bo'lmasa, memory'ga yozamiz (development)
        _memory_blacklist.add(token_hash)


def is_blacklisted(token: str) -> bool:
    """
    Refresh token blacklist da borligini tekshiradi.

    Returns:
        True — token blacklist da (yaroqsiz)
        False — token yaroqli
    """
    token_hash = _get_token_hash(token)
    key = f"{BLACKLIST_PREFIX}{token_hash}"

    try:
        return cache.get(key) is not None
    except Exception:
        # Redis mavjud bo'lmasa, memory'dan tekshirish
        return token_hash in _memory_blacklist


def blacklist_access_token(jti: str, lifetime_seconds: int | None = None) -> None:
    """
    Access tokenni JTI (JWT ID) orqali blacklist qiladi.
    Bu logout bo'lganda access token ham bekor qilinishi uchun ishlatiladi.
    """
    if lifetime_seconds is None:
        access_lifetime: timedelta = settings.SIMPLE_JWT.get(
            'ACCESS_TOKEN_LIFETIME', timedelta(hours=30)
        )
        lifetime_seconds = int(access_lifetime.total_seconds())

    key = f"{BLACKLIST_PREFIX}jti:{jti}"
    try:
        cache.set(key, "1", timeout=lifetime_seconds)
    except Exception:
        _memory_blacklist.add(f"jti:{jti}")


def is_access_token_blacklisted(jti: str) -> bool:
    """
    Access tokenning JTI si blacklist da borligini tekshiradi.
    """
    key = f"{BLACKLIST_PREFIX}jti:{jti}"
    try:
        return cache.get(key) is not None
    except Exception:
        return f"jti:{jti}" in _memory_blacklist
