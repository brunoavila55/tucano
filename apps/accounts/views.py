import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import TemplateView, UpdateView

from .forms import NotificationPreferenceForm
from .models import NotificationPreference, PushSubscription


class HomeView(TemplateView):
    template_name = "home.html"


class ProfileHubView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/profile_hub.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["has_professional_profile"] = hasattr(self.request.user, "professional_profile")
        context["has_client_profile"] = hasattr(self.request.user, "client_profile")
        return context


class NotificationPreferenceUpdateView(LoginRequiredMixin, UpdateView):
    model = NotificationPreference
    form_class = NotificationPreferenceForm
    template_name = "accounts/notification_preferences.html"
    success_url = reverse_lazy("profile-hub")

    def get_object(self, queryset=None):
        return NotificationPreference.for_user(self.request.user)


class PushSubscriptionCreateView(LoginRequiredMixin, View):
    """Recebe a inscrição de Web Push do service worker (JS ligado na Etapa 6/PWA)."""

    def post(self, request):
        try:
            data = json.loads(request.body)
            keys = data["keys"]
            PushSubscription.objects.update_or_create(
                endpoint=data["endpoint"],
                defaults={
                    "user": request.user,
                    "p256dh": keys["p256dh"],
                    "auth": keys["auth"],
                },
            )
        except (KeyError, json.JSONDecodeError):
            return JsonResponse({"error": "payload inválido"}, status=400)
        return JsonResponse({"status": "ok"})
