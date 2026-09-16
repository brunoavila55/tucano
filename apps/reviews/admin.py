from django.contrib import admin

from .models import Review, ServiceConfirmation


class ReviewInline(admin.TabularInline):
    model = Review
    extra = 0
    readonly_fields = ["author", "target", "rating", "comment", "contested", "contest_reason"]


@admin.register(ServiceConfirmation)
class ServiceConfirmationAdmin(admin.ModelAdmin):
    list_display = ["interest", "client_confirmed", "professional_confirmed", "asked_at"]
    inlines = [ReviewInline]


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ["author", "target", "rating", "contested", "created_at"]
    list_filter = ["contested", "rating"]
