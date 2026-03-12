from rest_framework import serializers
from apps.authentication.models import UserDevice


class UserDeviceSerializer(serializers.ModelSerializer):
    """Foydalanuvchi qurilma sessiyasini ko'rsatish uchun serializer."""

    class Meta:
        model = UserDevice
        fields = ['id', 'device_name', 'ip_address', 'created_at', 'last_active']
        read_only_fields = fields


class LoginSerializer(serializers.Serializer):
    """Login so'rovi uchun validatsiya."""
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True)


class RefreshSerializer(serializers.Serializer):
    """Token refresh so'rovi uchun validatsiya."""
    refresh = serializers.CharField()


class LogoutSerializer(serializers.Serializer):
    """Logout so'rovi uchun validatsiya."""
    refresh = serializers.CharField()
