from __future__ import annotations

from typing import Any

from django.core.cache import cache
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.request import Request
from rest_framework.response import Response

from ..models import User
from ..permissions import IsAdminRole
from ..serializers import UserSerializer, RegisterSerializer
from ..services.user_service import (
    approve_user,
    get_admin_stats,
    get_users_for_role,
    invalidate_user_caches,
    set_user_role,
    set_user_status,
)


class UserViewSet(viewsets.ModelViewSet):
    """
    Handles User CRUD using the service layer.
    """
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    pagination_class = None

    def get_queryset(self):
        return get_users_for_role(self.request.user)

    def list(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        if request.user.is_anonymous:
            cache_key = "api:users:public_curators"
            cached = cache.get(cache_key)
            if cached is not None:
                return Response(cached)
            response = super().list(request, *args, **kwargs)
            cache.set(cache_key, response.data, timeout=300)
            return response
        return super().list(request, *args, **kwargs)

    def perform_create(self, serializer: RegisterSerializer) -> None:
        super().perform_create(serializer)
        invalidate_user_caches()

    def perform_update(self, serializer: UserSerializer) -> None:
        super().perform_update(serializer)
        invalidate_user_caches()

    def destroy(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        if request.user.role != "admin":
            return Response(
                {"detail": "Faqat admin foydalanuvchini o'chira oladi."},
                status=status.HTTP_403_FORBIDDEN,
            )
        response = super().destroy(request, *args, **kwargs)
        invalidate_user_caches()
        return response


@api_view(["GET"])
@permission_classes([IsAdminRole])
def admin_stats(request: Request) -> Response:
    """Dashboard statistics for admins."""
    return Response(get_admin_stats())


@api_view(["PATCH"])
@permission_classes([IsAdminRole])
def admin_user_role(request: Request, pk: str) -> Response:
    """Changes a user's role."""
    try:
        user = User.objects.get(pk=pk)
    except User.DoesNotExist:
        return Response({"detail": "Foydalanuvchi topilmadi."}, status=status.HTTP_404_NOT_FOUND)

    new_role = request.data.get("role", user.role)
    try:
        set_user_role(user, new_role)
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    return Response(UserSerializer(user).data)


@api_view(["PATCH"])
@permission_classes([IsAdminRole])
def admin_user_status(request: Request, pk: str) -> Response:
    """Changes a user's status."""
    try:
        user = User.objects.get(pk=pk)
    except User.DoesNotExist:
        return Response({"detail": "Foydalanuvchi topilmadi."}, status=status.HTTP_404_NOT_FOUND)

    new_status = request.data.get("status", user.status)
    try:
        set_user_status(user, new_status)
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    return Response(UserSerializer(user).data)


@api_view(["POST"])
@permission_classes([IsAdminRole])
def admin_user_approve(request: Request, pk: str) -> Response:
    """Approves a pending user."""
    try:
        user = User.objects.get(pk=pk)
    except User.DoesNotExist:
        return Response({"detail": "Foydalanuvchi topilmadi."}, status=status.HTTP_404_NOT_FOUND)

    approve_user(user)
    return Response(UserSerializer(user).data)
