from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RegisterView, me, UserViewSet, SeasonViewSet, MonitoringViewSet, 
    WeeklyHighlightViewSet, NotificationViewSet, ChatMessageViewSet,
    PlatformSettingViewSet, admin_stats, admin_user_role, 
    admin_user_status, admin_user_approve, admin_notification_send,
    validate_intra
)

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='users')
router.register(r'seasons', SeasonViewSet, basename='seasons')
router.register(r'monitoring', MonitoringViewSet, basename='monitoring')
router.register(r'highlights', WeeklyHighlightViewSet, basename='highlights')
router.register(r'notifications', NotificationViewSet, basename='notifications')
router.register(r'settings', PlatformSettingViewSet, basename='settings')

urlpatterns = [
    # Router endpoints (monitoring, highlights, seasons, settings)
    path('', include(router.urls)),
    
    # Auth
    path('auth/register/', RegisterView.as_view(), name='auth_register'),
    path('auth/me/', me, name='auth_me'),
    path('auth/validate-intra/', validate_intra, name='auth_validate_intra'),
    
    # Chat
    path('chat/history/', ChatMessageViewSet.as_view({'get': 'list'}), name='chat_history'),
    path('chat/send/', ChatMessageViewSet.as_view({'post': 'create'}), name='chat_send'),
    
    # Admin
    path('admin/stats/', admin_stats, name='admin_stats'),
    path('admin/users/<uuid:pk>/role/', admin_user_role, name='admin_user_role'),
    path('admin/users/<uuid:pk>/status/', admin_user_status, name='admin_user_status'),
    path('admin/users/<uuid:pk>/approve/', admin_user_approve, name='admin_user_approve'),
    path('admin/notifications/send/', admin_notification_send, name='admin_notification_send'),
]
