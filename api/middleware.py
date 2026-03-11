from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken
from django.contrib.auth import get_user_model

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
            # More robust parsing for split values
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
                    print(f"DEBUG WS: User {user_id} authenticated via token")
                except Exception as e:
                    print(f"DEBUG WS: Token validation failed: {str(e)}")
                    scope["user"] = AnonymousUser()
            else:
                print("DEBUG WS: No token found in query string")
                scope["user"] = AnonymousUser()
        except Exception as e:
            print(f"DEBUG WS: Middleware error: {str(e)}")
            scope["user"] = AnonymousUser()

        return await self.inner(scope, receive, send)
