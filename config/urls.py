from django.contrib import admin
from django.urls import include, path

from apps.accounts.views import HomeView, ProfileHubView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("perfil/", ProfileHubView.as_view(), name="profile-hub"),
    path("profissional/", include("apps.professionals.urls")),
    path("contratante/", include("apps.clients.urls")),
    path("", HomeView.as_view(), name="home"),
]
