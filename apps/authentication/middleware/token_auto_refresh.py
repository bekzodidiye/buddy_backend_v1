"""
Token Auto-Refresh Middleware

Agar HTTP so'rovda access token muddati yaqin (1 soatdan kam qolgan) bo'lsa,
Response headerida yangi access token yuboradi.

Bu frontend dagi Axios interceptor bilan birgalikda ishlaydi —
frontend yangi tokenni avtomatik qabul qilib oladi.
"""
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import TokenError


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

        # Faqat authenticated requestlar uchun
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
                # Token muddati yaqin — yangi access token yaratib headerga qo'shamiz
                user_id = token.get('user_id')
                if user_id:
                    from django.contrib.auth import get_user_model
                    User = get_user_model()
                    try:
                        user = User.objects.get(id=user_id)
                        new_token = AccessToken.for_user(user)
                        response['X-New-Access-Token'] = str(new_token)
                    except User.DoesNotExist:
                        pass
        except (TokenError, Exception):
            # Token noto'g'ri — hech narsa qilmaymiz
            pass

        return response
