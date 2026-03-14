"""
api/services/monitoring_service.py — Business logic for Monitoring operations.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from django.db.models import Q, QuerySet

if TYPE_CHECKING:
    from api.models import Monitoring, User as UserType

logger = logging.getLogger(__name__)


def get_monitoring_queryset(user: "UserType") -> "QuerySet[Monitoring]":
    """
    Returns the Monitoring queryset scoped to the requesting user's visibility.

    Visibility rules:
      - admin   → all monitoring records
      - curator → only their own reports
      - student → only their own reports
    """
    from api.models import Monitoring

    base_qs = (
        Monitoring.objects
        .select_related("curator", "season", "student")
        .order_by("-id")
    )

    if user.role == "admin":
        return base_qs

    if user.role == "curator":
        return base_qs.filter(curator=user)

    # student
    return base_qs.filter(student=user)


def create_monitoring(data: dict[str, Any], curator: "UserType") -> "Monitoring":
    """
    Creates a new monitoring record.

    Args:
        data: Validated serializer data.
        curator: The user creating the record.

    Returns:
        The newly created Monitoring instance.
    """
    from api.models import Monitoring

    monitoring = Monitoring.objects.create(**data)
    logger.info(
        "Monitoring created: id=%s curator=%s week=%s",
        monitoring.id, curator.username, monitoring.week_number
    )
    return monitoring


def update_monitoring(
    monitoring: "Monitoring",
    data: dict[str, Any],
    partial: bool = False,
) -> "Monitoring":
    """
    Updates a monitoring record.

    Args:
        monitoring: The Monitoring instance to update.
        data: Validated serializer data.
        partial: Whether this is a partial (PATCH) update.

    Returns:
        The updated Monitoring instance.
    """
    changed_fields: list[str] = []
    for field, value in data.items():
        if getattr(monitoring, field) != value:
            setattr(monitoring, field, value)
            changed_fields.append(field)

    if changed_fields:
        monitoring.save(update_fields=changed_fields)
        logger.info(
            "Monitoring %s updated: fields=%s",
            monitoring.id, changed_fields
        )

    return monitoring


def get_notification_queryset(user: "UserType") -> "QuerySet":
    """
    Returns the Notification queryset visible to the given user.

    A notification is visible if:
      - It targets 'all' roles
      - It targets the user's specific role
      - It is addressed to this specific user
      - The user is admin (sees everything)
    """
    from api.models import Notification

    base_qs = (
        Notification.objects
        .select_related("target_user")
        .order_by("-timestamp")
    )

    if user.role == "admin":
        return base_qs

    return base_qs.filter(
        Q(target_role="all")
        | Q(target_role=user.role)
        | Q(target_user=user)
        | Q(target_role="none", target_user=user)
    ).distinct()
