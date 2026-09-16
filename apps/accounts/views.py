from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class HomeView(TemplateView):
    template_name = "home.html"


class ProfileHubView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/profile_hub.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["has_professional_profile"] = hasattr(self.request.user, "professional_profile")
        context["has_client_profile"] = hasattr(self.request.user, "client_profile")
        return context
