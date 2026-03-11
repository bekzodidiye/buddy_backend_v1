from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Notification, Monitoring
import json


def _safe_group_send(channel_layer, group_name, message):
    """channel_layer ga xavfsiz yuborish — xato bo'lsa log qilib o'tadi"""
    try:
        from asgiref.sync import async_to_sync
        # Serialize qilishda datetime muammosi bo'lmasli uchun
        # message dict ni JSON orqali tozalaymiz
        safe_message = json.loads(json.dumps(message, default=str))
        async_to_sync(channel_layer.group_send)(group_name, safe_message)
    except Exception as e:
        print(f"[Signal] group_send xatosi ({group_name}): {type(e).__name__}: {e}")


@receiver(post_save, sender=Notification)
def notify_realtime(sender, instance, created, **kwargs):
    if not created:
        return
    try:
        from channels.layers import get_channel_layer
        from .serializers import NotificationSerializer
        
        channel_layer = get_channel_layer()
        if channel_layer is None:
            return

        notification_data = dict(NotificationSerializer(instance).data)
        # UUID va datetime ni string ga aylantirish
        notification_data = json.loads(json.dumps(notification_data, default=str))

        message = {
            "type": "notification",
            "notification": notification_data
        }

        # Maxsus foydalanuvchiga yuborish
        if instance.target_user_id:
            _safe_group_send(channel_layer, f"user_{instance.target_user_id}", message)

        # Role guruhiga yuborish (none emas bo'lsa)
        if instance.target_role and instance.target_role not in ('all', 'none'):
            _safe_group_send(channel_layer, f"role_{instance.target_role}", message)

        # Barcha foydalanuvchilarga yuborish
        if instance.target_role == 'all':
            _safe_group_send(channel_layer, "all_users", message)

        # Admin guruhiga ham yuborish (ular ko'ra olsin)
        _safe_group_send(channel_layer, "role_admin", message)

    except Exception as e:
        print(f"[Signal] notify_realtime xatosi: {type(e).__name__}: {e}")


@receiver(post_save, sender=Monitoring)
def monitoring_realtime(sender, instance, created, **kwargs):
    try:
        from channels.layers import get_channel_layer
        from .serializers import MonitoringSerializer

        channel_layer = get_channel_layer()
        if channel_layer is None:
            return

        monitoring_data = json.loads(
            json.dumps(dict(MonitoringSerializer(instance).data), default=str)
        )

        message = {
            "type": "monitoring_update",
            "monitoring": monitoring_data
        }

        # Send to curator
        if instance.curator_id:
            _safe_group_send(channel_layer, f"user_{instance.curator_id}", message)

        # Send to student
        if instance.student_id:
            _safe_group_send(channel_layer, f"user_{instance.student_id}", message)

        # Send to admins
        _safe_group_send(channel_layer, "role_admin", message)

    except Exception as e:
        print(f"[Signal] monitoring_realtime xatosi: {type(e).__name__}: {e}")
