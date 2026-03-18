from __future__ import annotations

import logging

import requests
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.request import Request
from rest_framework.response import Response

from ..models import User
from ..serializers import (
    RegisterSerializer,
    UserSerializer,
)

logger = logging.getLogger(__name__)


class RegisterView(generics.CreateAPIView):
    """Public registration endpoint."""
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def me(request: Request) -> Response:
    """Returns the current authenticated user's profile."""
    user = (
        User.objects
        .prefetch_related("social_links")
        .get(pk=request.user.pk)
    )
    return Response(UserSerializer(user, context={"request": request}).data)


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def validate_intra(request: Request) -> Response:
    """
    Validates credentials against the 21 School Keycloak provider.
    """
    raw_username = request.data.get("username", "").strip()
    username = raw_username
    password = request.data.get("password", "")

    # For database check and standard intra login, we use lowercase login
    if "@" in username:
        username = username.split("@")[0]
    username = username.lower()

    if not username or not password:
        return Response(
            {"detail": "Username va parol kiritilishi shart."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if User.objects.filter(username=username).exists():
        return Response(
            {"detail": "Siz allaqachon ro'yxatdan o'tgansiz. Iltimos, login orqali kiring."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    keycloak_url = (
        "https://auth.21-school.ru/auth/realms/EduPowerKeycloak"
        "/protocol/openid-connect/token"
    )
    payload = {
        "client_id": "s21-open-api",
        "username": username,
        "password": password,
        "grant_type": "password",
    }
    _user_agent = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/91.0.4472.124 Safari/537.36"
    )
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": _user_agent,
        "Accept": "application/json",
    }
    
    # Standard payload for password grant
    payload = {
        "client_id": "s21-open-api",
        "username": username, # Try the extracted login first
        "password": password,
        "grant_type": "password",
        "scope": "openid profile email",
    }

    try:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        resp = requests.post(keycloak_url, data=payload, headers=headers, timeout=25, verify=False)
        
        # If login fails, try with raw_username (in case Keycloak expects full email or case-sensitive)
        if resp.status_code != 200 and raw_username != username:
            logger.info("Retrying Keycloak auth with raw username for '%s'", raw_username)
            payload["username"] = raw_username
            resp = requests.post(keycloak_url, data=payload, headers=headers, timeout=25, verify=False)

        if resp.status_code != 200:
            logger.warning("Keycloak auth failed for '%s': Status %s, Response: %s", username, resp.status_code, resp.text)
            return Response(
                {"detail": "School21 login yoki parol noto'g'ri. Iltimos, edu.21-school.ru dagi ma'lumotlaringizni tekshiring."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        token_data = resp.json()
        access_token: str = token_data.get("access_token", "")

        userinfo_url = (
            "https://auth.21-school.ru/auth/realms/EduPowerKeycloak"
            "/protocol/openid-connect/userinfo"
        )
        userinfo_resp = requests.get(
            userinfo_url,
            headers={"Authorization": f"Bearer {access_token}", "User-Agent": _user_agent},
            timeout=20,
            verify=False,
        )

        fullname = username
        email = f"{username}@student.21-school.ru"

        if userinfo_resp.status_code == 200:
            details = userinfo_resp.json()
            fullname = details.get("name") or details.get("preferred_username") or username
            email = details.get("email") or email

        return Response({"success": True, "username": username, "name": fullname, "email": email})

    except requests.exceptions.RequestException as exc:
        logger.error("Keycloak connection error for '%s': %s", username, exc)
        return Response(
            {"detail": "Maktab serveri bilan ulanishda xatolik. Keyinroq urinib ko'ring."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
