from django.contrib import admin
from apps.authentication.models import UserDevice


@admin.register(UserDevice)
class UserDeviceAdmin(admin.ModelAdmin):
    list_display = ['user', 'ip_address', 'device_name_short', 'created_at', 'last_active']
    list_filter = ['created_at', 'last_active']
    search_fields = ['user__username', 'user__name', 'ip_address', 'device_name']
    readonly_fields = ['created_at', 'last_active', 'refresh_token']
    ordering = ['-last_active']

    def device_name_short(self, obj):
        if obj.device_name:
            return obj.device_name[:80] + '...' if len(obj.device_name) > 80 else obj.device_name
        return 'Noma\'lum'
    device_name_short.short_description = 'Qurilma'
