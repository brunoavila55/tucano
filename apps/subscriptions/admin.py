from django.contrib import admin

from .models import Boost, Subscription


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ["user", "plan", "status", "current_period_end", "updated_at"]
    list_filter = ["plan", "status"]


@admin.register(Boost)
class BoostAdmin(admin.ModelAdmin):
    list_display = ["professional", "starts_at", "ends_at"]
