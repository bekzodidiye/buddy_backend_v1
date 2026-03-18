from __future__ import annotations

from rest_framework import serializers

from ..models import User, Notification, ChatMessage, PlatformSetting


class NotificationSerializer(serializers.ModelSerializer):
    targetRole = serializers.CharField(source='target_role', default='all', required=False)
    targetUserId = serializers.PrimaryKeyRelatedField(
        source='target_user',
        queryset=User.objects.all(),
        required=False,
        allow_null=True
    )
    isRead = serializers.BooleanField(source='is_read', default=False)
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)

    class Meta:
        model = Notification
        fields = [
            'id', 'title', 'message', 'type', 'timestamp', 'createdAt',
            'isRead', 'targetRole', 'targetUserId', 'sender'
        ]
        read_only_fields = ['timestamp', 'createdAt']


class ChatMessageSerializer(serializers.ModelSerializer):
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)

    class Meta:
        model = ChatMessage
        fields = ['id', 'role', 'text', 'createdAt']


class PlatformSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlatformSetting
        fields = ['key', 'value', 'description', 'updated_at']
        read_only_fields = ['updated_at']
