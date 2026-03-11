from django.contrib import admin
from .models import (
    User, SocialLink, Season, Monitoring, 
    WeeklyHighlight, Notification, ChatMessage, PlatformSetting
)

from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'name', 'role', 'status', 'is_approved', 'assigned_curator')
    list_filter = ('role', 'status', 'is_approved')
    search_fields = ('username', 'name', 'email')
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Buddy info', {'fields': ('name', 'role', 'status', 'avatar', 'field', 'long_bio', 'field_description', 'motivation_quote', 'skills', 'is_approved', 'assigned_curator')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Buddy info', {'fields': ('name', 'role', 'status', 'field', 'is_approved')}),
    )

@admin.register(SocialLink)
class SocialLinkAdmin(admin.ModelAdmin):
    list_display = ('user', 'link_url')

@admin.register(Season)
class SeasonAdmin(admin.ModelAdmin):
    list_display = ('number', 'start_date', 'is_active', 'duration_months')
    list_filter = ('is_active',)

@admin.register(Monitoring)
class MonitoringAdmin(admin.ModelAdmin):
    list_display = ('student', 'curator', 'season', 'week_number', 'status')
    list_filter = ('status', 'season', 'week_number')
    search_fields = ('student__username', 'curator__username')

@admin.register(WeeklyHighlight)
class WeeklyHighlightAdmin(admin.ModelAdmin):
    list_display = ('curator', 'season', 'week_number', 'uploaded_by')

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'type', 'target_role', 'is_read', 'timestamp')
    list_filter = ('type', 'target_role', 'is_read')

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'timestamp')
    list_filter = ('role',)

@admin.register(PlatformSetting)
class PlatformSettingAdmin(admin.ModelAdmin):
    list_display = ('key', 'value', 'description')
