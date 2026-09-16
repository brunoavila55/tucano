from django.urls import path

from . import views

app_name = "clients"

urlpatterns = [
    path("novo/", views.ClientProfileCreateView.as_view(), name="create"),
    path("painel/", views.ClientDashboardView.as_view(), name="dashboard"),
    path("favoritos/", views.FavoriteListView.as_view(), name="favorites"),
    path("favoritos/<int:professional_id>/alternar/", views.FavoriteToggleView.as_view(), name="favorite-toggle"),
]
