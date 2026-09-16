from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin

from .models import Interest, ServiceRequest


class InterestInline(admin.TabularInline):
    model = Interest
    extra = 0
    readonly_fields = ["professional", "message", "status", "created_at"]


@admin.register(ServiceRequest)
class ServiceRequestAdmin(GISModelAdmin):
    list_display = ["title", "client", "category", "status", "scheduled_start", "expires_at"]
    list_filter = ["status", "category", "interest_window"]
    inlines = [InterestInline]


@admin.register(Interest)
class InterestAdmin(admin.ModelAdmin):
    list_display = ["service_request", "professional", "status", "created_at"]
    list_filter = ["status"]
