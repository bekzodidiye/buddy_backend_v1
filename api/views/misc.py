from __future__ import annotations

from typing import Any

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.request import Request
from rest_framework.response import Response

from ..models import ChatMessage, Notification, PlatformSetting
from ..permissions import IsAdminRole
from ..serializers import (
    ChatMessageSerializer,
    NotificationSerializer,
    PlatformSettingSerializer,
)
from ..services.monitoring_service import (
    get_notification_queryset,
)


class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return get_notification_queryset(self.request.user)


class ChatMessageViewSet(viewsets.ModelViewSet):
    serializer_class = ChatMessageSerializer

    def get_queryset(self):
        return ChatMessage.objects.filter(user=self.request.user).order_by("created_at")

    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        text = request.data.get("text", "").strip()
        if not text:
            return Response(
                {"detail": "Xabar matni bo'sh bo'lishi mumkin emas."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user_msg = ChatMessage.objects.create(user=request.user, role="user", text=text)
        ai_msg = ChatMessage.objects.create(
            user=request.user,
            role="model",
            text=f"AI Buddy: Sizning xabaringizni qabul qildim. Qanday yordam berishim mumkin?",
        )
        return Response(
            ChatMessageSerializer([user_msg, ai_msg], many=True).data,
            status=status.HTTP_201_CREATED,
        )


class PlatformSettingViewSet(viewsets.ModelViewSet):
    queryset = PlatformSetting.objects.all()
    serializer_class = PlatformSettingSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    lookup_field = "key"


@api_view(["POST"])
@permission_classes([IsAdminRole])
def admin_notification_send(request: Request) -> Response:
    """Creates and broadcasts a notification."""
    serializer = NotificationSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
