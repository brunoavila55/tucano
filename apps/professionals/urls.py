from django.urls import path

from . import views

app_name = "professionals"

urlpatterns = [
    path("novo/", views.ProfessionalProfileCreateView.as_view(), name="create"),
    path("editar/", views.ProfessionalProfileUpdateView.as_view(), name="update"),
    path("painel/", views.ProfessionalDashboardView.as_view(), name="dashboard"),
    path("disponibilidade/nova/", views.AvailabilityCreateView.as_view(), name="availability-create"),
    path(
        "disponibilidade/<int:pk>/excluir/",
        views.AvailabilityDeleteView.as_view(),
        name="availability-delete",
    ),
    path("portfolio/novo/", views.PortfolioItemCreateView.as_view(), name="portfolio-create"),
    path(
        "portfolio/<int:pk>/excluir/",
        views.PortfolioItemDeleteView.as_view(),
        name="portfolio-delete",
    ),
    path("buscar/", views.ProfessionalSearchView.as_view(), name="search"),
]
