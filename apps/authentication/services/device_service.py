"""
Device Session Service — foydalanuvchi qurilmalarini boshqarish.
"""
import hashlib

from django.utils import timezone

from apps.authentication.models import UserDevice


def _hash_token(token: str) -> str:
    """Refresh tokenni hash qilib saqlaydi — xavfsizlik uchun."""
    return hashlib.sha256(token.encode()).hexdigest()


def get_client_ip(request) -> str | None:
    """Request dan real IP manzilni ajratib oladi (proxy va load balancer ni hisobga oladi)."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        # Bir nechta proxy bo'lsa, birinchisi real IP
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def get_device_name(request) -> str:
    """User-Agent headerdan qurilma nomini oladi."""
    return request.META.get('HTTP_USER_AGENT', 'Noma\'lum qurilma')[:512]


def create_device_session(user, request, refresh_token: str) -> UserDevice:
    """
    Yangi qurilma sessiyasini yaratadi yoki mavjudini yangilaydi.

    Agar xuddi shu qurilma (User-Agent + IP) dan avval ham kirgan bo'lsa,
    refresh tokenni yangilaydi — duplicate sessiyalar bo'lmaydi.
    """
    ip = get_client_ip(request)
    device_name = get_device_name(request)
    token_hash = _hash_token(refresh_token)

    # Bir xil qurilmadan ikkinchi marta kirish bo'lsa, yangilash
    device, created = UserDevice.objects.update_or_create(
        user=user,
        device_name=device_name,
        ip_address=ip,
        defaults={
            'refresh_token': token_hash,
            'last_active': timezone.now(),
        }
    )

    return device


def update_device_last_active(refresh_token: str) -> None:
    """
    Refresh token rotate bo'lganda, eski tokenni yangi bilan yangilaydi.
    """
    token_hash = _hash_token(refresh_token)
    try:
        device = UserDevice.objects.get(refresh_token=token_hash)
        device.last_active = timezone.now()
        device.save(update_fields=['last_active'])
    except UserDevice.DoesNotExist:
        pass


def update_device_token(old_refresh_token: str, new_refresh_token: str) -> None:
    """
    Token rotate bo'lganda qurilmaning refresh tokenini yangilaydi.
    """
    old_hash = _hash_token(old_refresh_token)
    new_hash = _hash_token(new_refresh_token)
    try:
        device = UserDevice.objects.get(refresh_token=old_hash)
        device.refresh_token = new_hash
        device.last_active = timezone.now()
        device.save(update_fields=['refresh_token', 'last_active'])
    except UserDevice.DoesNotExist:
        pass


def remove_device_session(refresh_token: str) -> bool:
    """
    Refresh token orqali qurilma sessiyasini o'chiradi (logout).

    Returns:
        True — session topildi va o'chirildi
        False — session topilmadi
    """
    token_hash = _hash_token(refresh_token)
    deleted_count, _ = UserDevice.objects.filter(refresh_token=token_hash).delete()
    return deleted_count > 0


def remove_device_by_id(device_id: str, user) -> bool:
    """
    ID bo'yicha qurilma sessiyasini o'chiradi (boshqa qurilmadan logout).
    Faqat o'z qurilmasini o'chira oladi.

    Returns:
        True — muvaffaqiyatli o'chirildi
        False — topilmadi yoki ruxsat yo'q
    """
    try:
        device = UserDevice.objects.get(id=device_id, user=user)
        device.delete()
        return True
    except UserDevice.DoesNotExist:
        return False


def get_user_devices(user) -> list[UserDevice]:
    """Foydalanuvchining barcha aktiv qurilmalarini ro'yxatini qaytaradi."""
    return UserDevice.objects.filter(user=user).order_by('-last_active')
