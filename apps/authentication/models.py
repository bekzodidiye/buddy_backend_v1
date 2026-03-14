import uuid
from django.db import models
from django.conf import settings


class UserDevice(models.Model):
    """
    Foydalanuvchining aktiv sessiyalarini kuzatib boradi.
    Bitta foydalanuvchi bir vaqtda bir nechta qurilmadan kirishi mumkin.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='devices',
        verbose_name='Foydalanuvchi'
    )
    device_name = models.CharField(
        max_length=512,
        null=True, blank=True,
        verbose_name='Qurilma nomi (User-Agent)'
    )
    ip_address = models.GenericIPAddressField(
        null=True, blank=True,
        verbose_name='IP manzili'
    )
    # FIX: Was TextField — SHA-256 hashes are always exactly 64 hex chars.
    # db_index=True turns every token refresh/logout from a full table scan → O(log N) lookup.
    refresh_token = models.CharField(
        max_length=64,
        verbose_name='Refresh token (hashed)',
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Yaratilgan vaqt')
    last_active = models.DateTimeField(auto_now=True, verbose_name='Oxirgi faollik')

    class Meta:
        verbose_name = 'Foydalanuvchi qurilmasi'
        verbose_name_plural = 'Foydalanuvchi qurilmalari'
        ordering = ['-last_active']
        indexes = [
            # FIX: Composite index for "get all devices for user" query
            models.Index(fields=['user', 'last_active'], name='device_user_last_active_idx'),
        ]

    def __str__(self):
        short_name = self.device_name[:50] if self.device_name else "Noma'lum qurilma"
        return f"{self.user.username} — {short_name}"
