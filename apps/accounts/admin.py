from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import NotificationLog, NotificationPreference, PushSubscription, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (("Contato", {"fields": ("phone_number",)}),)


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ["user", "push_enabled", "whatsapp_enabled", "email_enabled", "updated_at"]


@admin.register(PushSubscription)
class PushSubscriptionAdmin(admin.ModelAdmin):
    list_display = ["user", "endpoint", "created_at"]


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ["created_at", "user", "channel", "event_type", "status"]
    list_filter = ["channel", "status", "event_type"]

    def has_add_permission(self, request):
        return False
