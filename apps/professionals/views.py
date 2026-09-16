from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, TemplateView

from apps.accounts.mixins import ProfessionalRequiredMixin

from .models import ProfessionalProfile


class ProfessionalProfileCreateView(LoginRequiredMixin, CreateView):
    model = ProfessionalProfile
    fields = ["bio"]
    template_name = "professionals/profile_form.html"
    success_url = reverse_lazy("professionals:dashboard")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and hasattr(request.user, "professional_profile"):
            return redirect(self.success_url)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class ProfessionalDashboardView(ProfessionalRequiredMixin, TemplateView):
    template_name = "professionals/dashboard.html"
