from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path

from apps.accounts.views import (
    HomeView,
    NotificationPreferenceUpdateView,
    ProfileHubView,
    PushSubscriptionCreateView,
)

from .views import service_worker

urlpatterns = [
    path("admin/", admin.site.urls),
    path("sw.js", service_worker, name="service-worker"),
    path("accounts/", include("allauth.urls")),
    path("perfil/", ProfileHubView.as_view(), name="profile-hub"),
    path("perfil/notificacoes/", NotificationPreferenceUpdateView.as_view(), name="notification-preferences"),
    path("perfil/push/inscrever/", PushSubscriptionCreateView.as_view(), name="push-subscribe"),
    path("profissional/", include("apps.professionals.urls")),
    path("contratante/", include("apps.clients.urls")),
    path("chamados/", include("apps.requests.urls")),
    path("conversa/", include("apps.chat.urls")),
    path("avaliacoes/", include("apps.reviews.urls")),
    path("moderacao/", include("apps.moderation.urls")),
    path("", HomeView.as_view(), name="home"),
]

# Em produção o Caddy intercepta /static/* antes de chegar ao Django
# (docker/Caddyfile), então isso nunca é atingido lá — serve só para dev
# sem precisar rodar collectstatic, e para os testes. Por isso não é
# condicionado a settings.DEBUG: pytest-django força DEBUG=False depois
# que este módulo já foi importado, então um `if settings.DEBUG` aqui
# não pega o valor certo no momento certo.
urlpatterns += staticfiles_urlpatterns()
