from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, ListView, TemplateView, View

from apps.accounts.mixins import ClientRequiredMixin
from apps.professionals.models import ProfessionalProfile

from .models import ClientProfile, Favorite


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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["service_requests"] = self.request.user.client_profile.service_requests.all()[:20]
        return context


class FavoriteListView(ClientRequiredMixin, ListView):
    template_name = "clients/favorites.html"
    context_object_name = "favorites"

    def get_queryset(self):
        return self.request.user.client_profile.favorites.select_related(
            "professional__user", "professional__main_category"
        )


class FavoriteToggleView(ClientRequiredMixin, View):
    def post(self, request, professional_id):
        professional = get_object_or_404(ProfessionalProfile, pk=professional_id)
        favorite, created = Favorite.objects.get_or_create(
            client=request.user.client_profile, professional=professional
        )
        if not created:
            favorite.delete()
        next_url = request.POST.get("next") or reverse("clients:favorites")
        return redirect(next_url)
