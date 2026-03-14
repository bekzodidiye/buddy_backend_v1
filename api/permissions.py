from __future__ import annotations

from typing import Any

from rest_framework import permissions
from rest_framework.request import Request


class IsAdminRole(permissions.BasePermission):
    """Grants access only to users with role='admin'."""

    message = "Bu amalni faqat admin bajarishi mumkin."

    def has_permission(self, request: Request, view: Any) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "role", "") == "admin"
        )


class IsCuratorOrAdmin(permissions.BasePermission):
    """Grants access to curators and admins."""

    message = "Bu amalni faqat curator yoki admin bajarishi mumkin."

    def has_permission(self, request: Request, view: Any) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "role", "") in ("curator", "admin")
        )
