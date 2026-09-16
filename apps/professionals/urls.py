from django.urls import path

from . import views

app_name = "professionals"

urlpatterns = [
    path("novo/", views.ProfessionalProfileCreateView.as_view(), name="create"),
    path("painel/", views.ProfessionalDashboardView.as_view(), name="dashboard"),
]
