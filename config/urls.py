from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

# Eski Axios interceptor uchun backward compatibility
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('admin/', admin.site.urls),

    # Asosiy API endpointlar
    path('api/v1/', include('api.urls')),

    # === Yangi Autentifikatsiya tizimi ===
    # POST /api/v1/auth/login/    — login + qurilma sessiyasi
    # POST /api/v1/auth/refresh/  — token rotation
    # POST /api/v1/auth/logout/   — blacklist + sessiya o'chirish
    # GET  /api/v1/auth/devices/  — qurilmalar ro'yxati
    # DEL  /api/v1/auth/devices/<id>/ — qurilmadan chiqish
    path('api/v1/auth/', include('apps.authentication.urls')),

    # === Eski endpoint (Axios interceptor bilan backward compatible) ===
    # Frontend dagi api.ts da ishlatiladigan:
    # POST /api/v1/auth/token/refresh/ — hali ishlab beradi
    path('api/v1/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh_legacy'),

    # API Schema (Swagger)
    path('api/v1/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/v1/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/v1/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

