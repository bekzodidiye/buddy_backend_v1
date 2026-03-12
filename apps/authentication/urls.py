from django.urls import path
from . import views

urlpatterns = [
    # Login — JWT tokenlar + qurilma sessiyasi
    path('login/', views.login_view, name='auth_login'),

    # Token yangilash — rotation bilan
    path('refresh/', views.refresh_view, name='auth_refresh'),

    # Logout — blacklist + sessiyani o'chirish
    path('logout/', views.logout_view, name='auth_logout'),

    # Qurilmalar ro'yxati
    path('devices/', views.devices_list_view, name='auth_devices_list'),

    # Muayyan qurilmadan chiqish
    path('devices/<uuid:device_id>/', views.device_delete_view, name='auth_device_delete'),
]
