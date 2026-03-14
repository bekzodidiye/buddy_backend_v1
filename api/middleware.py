"""
api/middleware.py — WebSocket JWT Auth Middleware (Fixed)

Changes:
  - FIX: Replaced all print() with logger.debug(). Debug-level WS auth
    messages were going to stdout on every WebSocket connection, flooding
    production logs.
"""
import logging

from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)

User = get_user_model()


@database_sync_to_async
def get_user(user_id):
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return AnonymousUser()


class JWTAuthMiddleware:
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        try:
            query_string = scope.get("query_string", b"").decode("utf-8")
            query_params = {}
            for pair in query_string.split("&"):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    query_params[k] = v

            token = query_params.get("token")

            if token:
                try:
                    access_token = AccessToken(token)
                    user_id = access_token["user_id"]
                    scope["user"] = await get_user(user_id)
                    logger.debug("WS: User %s authenticated via token", user_id)
                except Exception as e:
                    logger.warning("WS: Token validation failed: %s", str(e))
                    scope["user"] = AnonymousUser()
            else:
                logger.debug("WS: No token found in query string — anonymous user")
                scope["user"] = AnonymousUser()
        except Exception as e:
            logger.error("WS: Middleware error: %s", str(e))
            scope["user"] = AnonymousUser()

        return await self.inner(scope, receive, send)
