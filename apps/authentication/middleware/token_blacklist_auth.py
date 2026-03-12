"""
Custom JWT Authentication — Redis blacklist tekshirish bilan.

SimpleJWT ning standart JWTAuthentication klassini kengaytiradi:
har bir authenticated request da access tokenning JTI si
Redis blacklist da borligini tekshiradi.
"""
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from rest_framework.exceptions import AuthenticationFailed

from apps.authentication.services.token_blacklist import is_access_token_blacklisted


class BlacklistCheckedJWTAuthentication(JWTAuthentication):
    """
    Standart JWTAuthentication ustiga blacklist tekshiruvini qo'shadi.
    
    Agar logout bo'lgan foydalanuvchi eski access token bilan kirmoqchi bo'lsa,
    401 Unauthorized qaytaradi — garchi token muddati o'tmagan bo'lsa ham.
    """

    def get_validated_token(self, raw_token):
        # Avval standart SimpleJWT validatsiyasi
        validated_token = super().get_validated_token(raw_token)

        # Keyin Redis blacklist tekshirish
        jti = validated_token.get('jti')
        if jti and is_access_token_blacklisted(jti):
            raise AuthenticationFailed(
                detail='Token yaroqsiz qilingan (logout bo\'lgan). Qayta kiring.',
                code='token_blacklisted'
            )

        return validated_token
