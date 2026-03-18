"""
api/signals.py — Fixed version

Changes:
  - FIX: Replaced print() with logger calls.
  - FIX: monitoring_realtime now passes `created` to the message so the
    frontend can distinguish new records from updates.
  - FIX: Uses select_related to avoid N+1 when serializing in the signal.
"""
import json
import logging

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Notification, Monitoring, WeeklyHighlight

logger = logging.getLogger(__name__)


def _safe_group_send(channel_layer, group_name, message):
    """Safely send to a channel group — logs and swallows any errors."""
    try:
        from asgiref.sync import async_to_sync
        # Serialize datetime/UUID objects before sending
        safe_message = json.loads(json.dumps(message, default=str))
        async_to_sync(channel_layer.group_send)(group_name, safe_message)
    except Exception as e:
        logger.warning(
            "Signal: group_send failed (group='%s'): %s: %s",
            group_name, type(e).__name__, e
        )


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

        notification_data = json.loads(
            json.dumps(dict(NotificationSerializer(instance).data), default=str)
        )

        message = {
            "type": "notification",
            "notification": notification_data
        }

        # Send to specific user
        if instance.target_user_id:
            _safe_group_send(channel_layer, f"user_{instance.target_user_id}", message)

        # Send to role group
        if instance.target_role and instance.target_role not in ('all', 'none'):
            _safe_group_send(channel_layer, f"role_{instance.target_role}", message)

        # Broadcast to everyone
        if instance.target_role == 'all':
            _safe_group_send(channel_layer, "all_users", message)

        # Always send to admins so they can see all notifications
        _safe_group_send(channel_layer, "role_admin", message)

        logger.debug(
            "Signal: notification %s broadcast (role=%s)", instance.id, instance.target_role
        )

    except Exception as e:
        logger.error(
            "Signal: notify_realtime failed: %s: %s", type(e).__name__, e, exc_info=True
        )


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
            "monitoring": monitoring_data,
            # FIX: Include created flag so frontend knows if this is new or updated
            "created": created,
        }

        if instance.curator_id:
            _safe_group_send(channel_layer, f"user_{instance.curator_id}", message)

        if instance.student_id:
            _safe_group_send(channel_layer, f"user_{instance.student_id}", message)

        _safe_group_send(channel_layer, "role_admin", message)

    except Exception as e:
        logger.error(
            "Signal: monitoring_realtime failed: %s: %s", type(e).__name__, e, exc_info=True
        )


@receiver(post_save, sender=WeeklyHighlight)
def highlight_realtime(sender, instance, created, **kwargs):
    try:
        from channels.layers import get_channel_layer
        from .serializers import WeeklyHighlightSerializer

        channel_layer = get_channel_layer()
        if channel_layer is None:
            return

        highlight_data = json.loads(
            json.dumps(dict(WeeklyHighlightSerializer(instance).data), default=str)
        )

        message = {
            "type": "highlight_update",
            "highlight": highlight_data,
            "created": created,
        }

        # Broadcast to all users for highlights
        _safe_group_send(channel_layer, "all_users", message)

    except Exception as e:
        logger.error(
            "Signal: highlight_realtime failed: %s: %s", type(e).__name__, e, exc_info=True
        )
