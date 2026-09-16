from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, TemplateView

from apps.accounts.mixins import ClientRequiredMixin

from .models import ClientProfile


class ClientProfileCreateView(LoginRequiredMixin, CreateView):
    model = ClientProfile
    fields = ["company_name"]
    template_name = "clients/profile_form.html"
    success_url = reverse_lazy("clients:dashboard")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and hasattr(request.user, "client_profile"):
            return redirect(self.success_url)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class ClientDashboardView(ClientRequiredMixin, TemplateView):
    template_name = "clients/dashboard.html"
