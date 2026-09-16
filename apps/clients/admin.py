from django.contrib import admin

from .models import ClientProfile, Favorite

admin.site.register(ClientProfile)


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ["client", "professional", "created_at"]
