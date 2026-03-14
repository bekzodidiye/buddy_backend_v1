"""
api/tasks.py — Celery background tasks

Heavy or slow operations moved out of the request-response cycle:
  - External HTTP calls (Keycloak validation)
  - Bulk notification sending
  - Periodic cache warming
  - Database statistics aggregation
"""
import logging

from celery import shared_task
from django.core.cache import cache
from django.db.models import Count, Q

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3},
    retry_backoff=True,
    name='api.tasks.send_bulk_notification'
)
def send_bulk_notification(self, title: str, message: str, notification_type: str,
                           target_role: str = 'all', sender: str = None):
    """
    Creates and broadcasts a notification asynchronously.
    
    Moved to a Celery task so the admin endpoint returns immediately,
    and the DB write + WebSocket broadcast happen in the background.
    
    Usage:
        send_bulk_notification.delay('Title', 'Message', 'info', target_role='all')
    """
    from api.models import Notification

    try:
        notification = Notification.objects.create(
            title=title,
            message=message,
            type=notification_type,
            target_role=target_role,
            sender=sender,
        )
        logger.info(
            "Bulk notification sent: id=%s role=%s", notification.id, target_role
        )
        return {'id': str(notification.id), 'status': 'sent'}
    except Exception as exc:
        logger.error("Failed to send bulk notification: %s", exc, exc_info=True)
        raise  # Let Celery handle the retry


@shared_task(name='api.tasks.warm_admin_stats_cache')
def warm_admin_stats_cache():
    """
    Periodic task — pre-computes and caches admin stats so the dashboard
    responds immediately instead of running aggregations on demand.
    
    Schedule this to run every 5 minutes via Celery Beat.
    """
    from api.models import User, Monitoring

    try:
        user_stats = User.objects.aggregate(
            total=Count('id'),
            active_curators=Count('id', filter=Q(role='curator', is_approved=True)),
        )
        monitoring_count = Monitoring.objects.count()

        data = {
            "total_users": user_stats['total'],
            "total_monitorings": monitoring_count,
            "active_curators": user_stats['active_curators'],
        }

        cache.set('api:admin:stats', data, timeout=300)
        logger.info("Admin stats cache warmed: %s", data)
        return data
    except Exception as exc:
        logger.error("Failed to warm admin stats cache: %s", exc, exc_info=True)
        raise


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 2},
    retry_backoff=True,
    name='api.tasks.cleanup_expired_devices'
)
def cleanup_expired_devices(self):
    """
    Periodic task — removes UserDevice records older than 30 days.
    Prevents the devices table from growing unboundedly.
    
    Schedule this to run daily via Celery Beat.
    """
    from django.utils import timezone
    from datetime import timedelta
    from apps.authentication.models import UserDevice

    cutoff = timezone.now() - timedelta(days=30)
    try:
        deleted_count, _ = UserDevice.objects.filter(last_active__lt=cutoff).delete()
        logger.info("Cleaned up %d expired device sessions.", deleted_count)
        return {'deleted': deleted_count}
    except Exception as exc:
        logger.error("Device cleanup failed: %s", exc, exc_info=True)
        raise


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 2},
    retry_backoff=True,
    name='api.tasks.invalidate_user_cache'
)
def invalidate_user_cache(self, user_id: str = None):
    """
    Invalidates cached user-related data after profile updates.
    Called automatically after user save/delete operations.
    """
    try:
        cache.delete('api:users:public_curators')
        cache.delete('api:admin:stats')
        if user_id:
            cache.delete(f'api:users:{user_id}')
        logger.debug("User cache invalidated for user_id=%s", user_id)
    except Exception as exc:
        logger.warning("Cache invalidation failed: %s", exc)
