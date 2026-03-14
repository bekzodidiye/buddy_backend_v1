"""
api/services/user_service.py — Business logic for User operations.

All data-access + business rules related to User are here.
Views only call these functions — no raw ORM in views.

Why a service layer?
  - Views stay thin and readable (HTTP concern only)
  - Services are unit-testable without HTTP overhead
  - Business rules live in one place (DRY)
  - Easy to replace ORM calls with cache hits
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django.core.cache import cache
from django.db.models import Count, Q, QuerySet

if TYPE_CHECKING:
    from api.models import User as UserType

logger = logging.getLogger(__name__)

# Cache key constants — defined once, used everywhere
CACHE_PUBLIC_CURATORS = "api:users:public_curators"
CACHE_ADMIN_STATS = "api:admin:stats"
CACHE_TTL_MEDIUM = 300   # 5 minutes
CACHE_TTL_SHORT = 60     # 1 minute


def get_public_curators(*, use_cache: bool = True) -> "QuerySet[UserType]":
    """
    Returns the queryset of active, approved curators visible to everyone.

    Args:
        use_cache: If True, returns cached results when available.
                   Set to False in tests or after mutations.
    """
    from api.models import User

    if use_cache:
        cached = cache.get(CACHE_PUBLIC_CURATORS)
        if cached is not None:
            logger.debug("Cache HIT: %s", CACHE_PUBLIC_CURATORS)
            return cached

    qs = (
        User.objects
        .filter(role="curator", status="active", is_approved=True)
        .prefetch_related("social_links")
        .order_by("username")
    )
    # We cannot cache a lazy queryset — evaluate it so it's serialisable
    result = list(qs)
    if use_cache:
        cache.set(CACHE_PUBLIC_CURATORS, result, timeout=CACHE_TTL_MEDIUM)
    return qs  # Return the original queryset for DRF serialisation


def get_users_for_role(user: "UserType") -> "QuerySet[UserType]":
    """
    Returns the visible User queryset based on the requesting user's role.

    Role visibility rules:
      - admin   → all users
      - curator → students + active approved users + self
      - student → active approved users + self
      - anon    → public curators only
    """
    from api.models import User

    base_qs = User.objects.prefetch_related("social_links").order_by("username")

    if user.is_anonymous:
        return base_qs.filter(role="curator", status="active", is_approved=True)

    if user.role == "admin":
        return base_qs.all()

    base_filter = Q(status="active", is_approved=True) | Q(id=user.id)

    if user.role == "curator":
        return base_qs.filter(Q(role="student") | base_filter).distinct()

    return base_qs.filter(base_filter).distinct()


def approve_user(user: "UserType") -> "UserType":
    """
    Approves a user: sets is_approved=True, status=active.
    Invalidates relevant caches.
    """
    user.is_approved = True
    user.status = "active"
    user.save(update_fields=["is_approved", "status"])
    invalidate_user_caches()
    logger.info("User %s approved.", user.username)
    return user


def set_user_role(user: "UserType", role: str) -> "UserType":
    """
    Sets the user's role. Validates against allowed choices.

    Raises:
        ValueError: If role is not a valid choice.
    """
    from api.models import User

    valid_roles = {choice[0] for choice in User.ROLE_CHOICES}
    if role not in valid_roles:
        raise ValueError(f"Invalid role '{role}'. Allowed: {', '.join(sorted(valid_roles))}")

    user.role = role
    user.save(update_fields=["role"])
    invalidate_user_caches()
    logger.info("User %s role updated to '%s'.", user.username, role)
    return user


def set_user_status(user: "UserType", status: str) -> "UserType":
    """
    Sets the user's status. Validates against allowed choices.

    Raises:
        ValueError: If status is not a valid choice.
    """
    from api.models import User

    valid_statuses = {choice[0] for choice in User.STATUS_CHOICES}
    if status not in valid_statuses:
        raise ValueError(
            f"Invalid status '{status}'. Allowed: {', '.join(sorted(valid_statuses))}"
        )

    user.status = status
    user.save(update_fields=["status"])
    invalidate_user_caches()
    logger.info("User %s status updated to '%s'.", user.username, status)
    return user


def invalidate_user_caches() -> None:
    """Deletes all user-related cache keys. Call after any user mutation."""
    cache.delete_many([CACHE_PUBLIC_CURATORS, CACHE_ADMIN_STATS])
    logger.debug("User caches invalidated.")


def get_admin_stats() -> dict:
    """
    Returns dashboard statistics for admin users.
    Caches the result for CACHE_TTL_SHORT seconds.
    """
    from api.models import Monitoring, User

    cached = cache.get(CACHE_ADMIN_STATS)
    if cached is not None:
        logger.debug("Cache HIT: %s", CACHE_ADMIN_STATS)
        return cached

    user_stats = User.objects.aggregate(
        total=Count("id"),
        active_curators=Count("id", filter=Q(role="curator", is_approved=True)),
        pending_users=Count("id", filter=Q(status="pending")),
    )
    monitoring_count = Monitoring.objects.count()

    data: dict = {
        "total_users": user_stats["total"],
        "total_monitorings": monitoring_count,
        "active_curators": user_stats["active_curators"],
        "pending_users": user_stats["pending_users"],
    }

    cache.set(CACHE_ADMIN_STATS, data, timeout=CACHE_TTL_SHORT)
    return data
