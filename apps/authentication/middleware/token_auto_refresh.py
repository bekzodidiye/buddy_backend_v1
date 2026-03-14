"""
Token Auto-Refresh Middleware — Fixed version

Changes:
  - FIX: Was doing User.objects.get(id=user_id) on EVERY request that had
    a nearly-expired token. The user is already loaded by the authentication
    backend — we use request.user directly, eliminating the extra DB query.
  - FIX: Replaced print() with proper logging.
"""
import logging
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import TokenError

logger = logging.getLogger(__name__)


class TokenAutoRefreshMiddleware:
    """
    Production middleware — token muddati yaqin bo'lganda yangi token chiqaradi.

    Response da `X-New-Access-Token` header yuboriladi.
    Frontend bu headerni ko'rib, localStorage ni yangilashi kerak.
    """

    THRESHOLD_SECONDS = 3600  # 1 soat qolganda yangilash

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Only for authenticated requests
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if not auth_header.startswith('Bearer '):
            return response

        raw_token = auth_header.split(' ', 1)[1].strip()

        try:
            token = AccessToken(raw_token)
            exp = token['exp']
            now_ts = int(timezone.now().timestamp())
            remaining = exp - now_ts

            if 0 < remaining < self.THRESHOLD_SECONDS:
                # FIX: request.user is ALREADY set by BlacklistCheckedJWTAuthentication.
                # The original code did User.objects.get(id=user_id) here — an extra
                # DB round-trip on every single request where the token is nearly expired.
                user = getattr(request, 'user', None)
                if user and user.is_authenticated:
                    new_token = AccessToken.for_user(user)
                    response['X-New-Access-Token'] = str(new_token)
                    logger.debug(
                        "Auto-refreshed access token for user %s (%.0fs remaining)",
                        user.id, remaining
                    )

        except (TokenError, Exception):
            # Token is invalid — do nothing, let the auth backend handle it
            pass

        return response
