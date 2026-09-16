from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin

from .models import Availability, PortfolioItem, ProfessionalProfile, ServiceCategory


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "is_active"]
    list_filter = ["is_active"]
    prepopulated_fields = {"slug": ("name",)}


class AvailabilityInline(admin.TabularInline):
    model = Availability
    extra = 0


class PortfolioItemInline(admin.TabularInline):
    model = PortfolioItem
    extra = 0


@admin.register(ProfessionalProfile)
class ProfessionalProfileAdmin(GISModelAdmin):
    list_display = ["user", "main_category", "location_label", "is_available_now"]
    list_filter = ["main_category", "is_available_now"]
    inlines = [AvailabilityInline, PortfolioItemInline]
