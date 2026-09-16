from django.contrib import admin
from django.urls import include, path

from apps.accounts.views import (
    HomeView,
    NotificationPreferenceUpdateView,
    ProfileHubView,
    PushSubscriptionCreateView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("perfil/", ProfileHubView.as_view(), name="profile-hub"),
    path("perfil/notificacoes/", NotificationPreferenceUpdateView.as_view(), name="notification-preferences"),
    path("perfil/push/inscrever/", PushSubscriptionCreateView.as_view(), name="push-subscribe"),
    path("profissional/", include("apps.professionals.urls")),
    path("contratante/", include("apps.clients.urls")),
    path("chamados/", include("apps.requests.urls")),
    path("conversa/", include("apps.chat.urls")),
    path("", HomeView.as_view(), name="home"),
]
