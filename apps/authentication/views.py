"""
Authentication Views — login, refresh, logout, devices.

Bu views mavjud SimpleJWT standarti ustiga quyidagilarni qo'shadi:
- Redis blacklist
- Multi-device session tracking
- Refresh token rotation
- Qurilma boshqaruvi (ko'rish va o'chirish)
"""
from django.contrib.auth import authenticate, get_user_model
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from apps.authentication.serializers import (
    LoginSerializer, RefreshSerializer, LogoutSerializer, UserDeviceSerializer
)
from apps.authentication.services.token_blacklist import (
    blacklist_token, is_blacklisted,
    blacklist_access_token
)
from apps.authentication.services.device_service import (
    create_device_session, update_device_token,
    remove_device_session, remove_device_by_id, get_user_devices
)

User = get_user_model()


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """
    POST /api/v1/auth/login/

    Foydalanuvchini autentifikatsiya qiladi, JWT tokenlar chiqaradi
    va qurilma sessiyasini saqlaydi.

    Request body:
        { "username": "...", "password": "..." }

    Response:
        { "access": "...", "refresh": "...", "user": {...} }
    """
    serializer = LoginSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    username = serializer.validated_data['username']
    password = serializer.validated_data['password']

    # Kichik harflarga o'tkazish (username case-insensitive)
    username = username.lower().strip()

    user = authenticate(request, username=username, password=password)

    if user is None:
        return Response(
            {'detail': 'Username yoki parol noto\'g\'ri.'},
            status=status.HTTP_401_UNAUTHORIZED
        )

    if not user.is_active:
        return Response(
            {'detail': 'Akkaunt faolsizlantirilgan.'},
            status=status.HTTP_403_FORBIDDEN
        )

    # JWT tokenlar yaratish
    refresh = RefreshToken.for_user(user)
    access = str(refresh.access_token)
    refresh_str = str(refresh)

    # Qurilma sessiyasini saqlash
    create_device_session(user, request, refresh_str)

    # Foydalanuvchi ma'lumotlari
    from api.serializers import UserSerializer
    user_data = UserSerializer(user, context={'request': request}).data

    return Response({
        'access': access,
        'refresh': refresh_str,
        'user': user_data,
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def refresh_view(request):
    """
    POST /api/v1/auth/refresh/

    Refresh token orqali yangi access va refresh tokenlar chiqaradi.
    Refresh token rotation amalga oshiriladi:
    - Eski refresh token blacklist qilinadi
    - Yangi access + refresh token chiqariladi
    - Qurilma sessiyasi yangilanadi

    Bu token replay attack lardan himoya qiladi.

    Request body:
        { "refresh": "old_refresh_token" }

    Response:
        { "access": "new_access_token", "refresh": "new_refresh_token" }
    """
    serializer = RefreshSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    old_refresh_str = serializer.validated_data['refresh']

    # Blacklist tekshirish — eski token ishlatilgan bo'lsa, token theft deb hisoblash
    if is_blacklisted(old_refresh_str):
        return Response(
            {'detail': 'Token allaqachon ishlatilgan yoki bekor qilingan. Qayta kiring.'},
            status=status.HTTP_401_UNAUTHORIZED
        )

    try:
        refresh = RefreshToken(old_refresh_str)
    except TokenError as e:
        return Response(
            {'detail': f'Refresh token noto\'g\'ri yoki muddati o\'tgan: {str(e)}'},
            status=status.HTTP_401_UNAUTHORIZED
        )

    # Rotation: eski token ni blacklist qilish
    blacklist_token(old_refresh_str)

    # Yangi token juftligi yaratish
    user_id = refresh.payload.get('user_id')
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({'detail': 'Foydalanuvchi topilmadi.'}, status=status.HTTP_401_UNAUTHORIZED)

    new_refresh = RefreshToken.for_user(user)
    new_refresh_str = str(new_refresh)
    new_access_str = str(new_refresh.access_token)

    # Qurilma sessiyasini yangilanayotgan tokenlar bilan yangilash
    update_device_token(old_refresh_str, new_refresh_str)

    return Response({
        'access': new_access_str,
        'refresh': new_refresh_str,
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """
    POST /api/v1/auth/logout/

    Joriy qurilma sessiyasidan chiqish:
    1. Refresh token blacklist qilinadi (Redis)
    2. Access token JTI si blacklist qilinadi
    3. Qurilma sessiyasi o'chiriladi

    Request body (ixtiyoriy — agar yo'q bo'lsa, faqat access blacklist):
        { "refresh": "refresh_token" }
    """
    refresh_str = request.data.get('refresh')

    # Access token JTI si ni blacklist qilish (agar mavjud bo'lsa)
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    if auth_header.startswith('Bearer '):
        try:
            from rest_framework_simplejwt.tokens import AccessToken
            raw_token = auth_header.split(' ', 1)[1].strip()
            access_token = AccessToken(raw_token)
            jti = access_token.get('jti')
            if jti:
                blacklist_access_token(jti)
        except Exception:
            pass  # Token noto'g'ri bo'lsa ham logout qilishga ruxsat

    # Refresh token blacklist + sessiya o'chirish
    if refresh_str:
        if not is_blacklisted(refresh_str):
            blacklist_token(refresh_str)
        remove_device_session(refresh_str)

    return Response({'detail': 'Muvaffaqiyatli chiqildi.'}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def devices_list_view(request):
    """
    GET /api/v1/auth/devices/

    Foydalanuvchining barcha aktiv qurilmalar (sessiyalar) ro'yxatini qaytaradi.

    Response:
        [
            {
                "id": "uuid",
                "device_name": "Mozilla/5.0...",
                "ip_address": "192.168.1.1",
                "created_at": "2026-03-12T...",
                "last_active": "2026-03-12T..."
            },
            ...
        ]
    """
    devices = get_user_devices(request.user)
    serializer = UserDeviceSerializer(devices, many=True)
    return Response(serializer.data)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def device_delete_view(request, device_id):
    """
    DELETE /api/v1/auth/devices/{device_id}/

    Muayyan qurilma sessiyasini o'chiradi (remote logout).
    Foydalanuvchi faqat o'z qurilmalarini o'chira oladi.

    Response:
        { "detail": "Qurilma sessiyasi tugatildi." }
    """
    success = remove_device_by_id(device_id, request.user)
    if success:
        return Response({'detail': 'Qurilma sessiyasi tugatildi.'}, status=status.HTTP_200_OK)
    return Response(
        {'detail': 'Qurilma topilmadi yoki ruxsat yo\'q.'},
        status=status.HTTP_404_NOT_FOUND
    )
