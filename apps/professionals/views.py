from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.db.models import Exists, OuterRef
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, ListView, TemplateView, UpdateView

from apps.accounts.mixins import ProfessionalRequiredMixin
from apps.subscriptions.models import Boost

from .forms import AvailabilityForm, PortfolioItemForm, ProfessionalProfileForm
from .models import Availability, PortfolioItem, ProfessionalProfile, ServiceCategory


class ProfessionalProfileCreateView(LoginRequiredMixin, CreateView):
    model = ProfessionalProfile
    form_class = ProfessionalProfileForm
    template_name = "professionals/profile_form.html"
    success_url = reverse_lazy("professionals:dashboard")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and hasattr(request.user, "professional_profile"):
            return redirect(self.success_url)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class ProfessionalProfileUpdateView(ProfessionalRequiredMixin, UpdateView):
    model = ProfessionalProfile
    form_class = ProfessionalProfileForm
    template_name = "professionals/profile_form.html"
    success_url = reverse_lazy("professionals:dashboard")

    def get_object(self, queryset=None):
        return self.request.user.professional_profile


class ProfessionalDashboardView(ProfessionalRequiredMixin, TemplateView):
    template_name = "professionals/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.request.user.professional_profile
        context["profile"] = profile
        context["availabilities"] = profile.availabilities.all()
        context["portfolio_items"] = profile.portfolio_items.all()
        return context


class AvailabilityCreateView(ProfessionalRequiredMixin, CreateView):
    model = Availability
    form_class = AvailabilityForm
    template_name = "professionals/availability_form.html"
    success_url = reverse_lazy("professionals:dashboard")

    def form_valid(self, form):
        form.instance.professional = self.request.user.professional_profile
        return super().form_valid(form)


class AvailabilityDeleteView(ProfessionalRequiredMixin, DeleteView):
    model = Availability
    success_url = reverse_lazy("professionals:dashboard")
    template_name = "professionals/availability_confirm_delete.html"

    def get_queryset(self):
        return Availability.objects.filter(professional=self.request.user.professional_profile)


class PortfolioItemCreateView(ProfessionalRequiredMixin, CreateView):
    model = PortfolioItem
    form_class = PortfolioItemForm
    template_name = "professionals/portfolio_form.html"
    success_url = reverse_lazy("professionals:dashboard")

    def form_valid(self, form):
        form.instance.professional = self.request.user.professional_profile
        return super().form_valid(form)


class PortfolioItemDeleteView(ProfessionalRequiredMixin, DeleteView):
    model = PortfolioItem
    success_url = reverse_lazy("professionals:dashboard")
    template_name = "professionals/portfolio_confirm_delete.html"

    def get_queryset(self):
        return PortfolioItem.objects.filter(professional=self.request.user.professional_profile)


class ProfessionalSearchView(ListView):
    model = ProfessionalProfile
    template_name = "professionals/search.html"
    context_object_name = "professionals"
    paginate_by = 10

    def get_queryset(self):
        qs = ProfessionalProfile.objects.select_related("main_category").exclude(location__isnull=True)

        category_slug = self.request.GET.get("categoria")
        if category_slug:
            qs = qs.filter(main_category__slug=category_slug)

        # Boost só reordena dentro do conjunto já compatível (categoria/região
        # filtradas acima) — nunca promove um perfil incompatível
        # (AGENTS.md — "Encontrar profissionais").
        now = timezone.now()
        active_boosts = Boost.objects.filter(professional=OuterRef("pk"), starts_at__lte=now, ends_at__gte=now)
        qs = qs.annotate(is_boosted=Exists(active_boosts))

        lat = self.request.GET.get("lat")
        lon = self.request.GET.get("lon")
        origin = self._parse_point(lat, lon)
        if origin is not None:
            return qs.annotate(distance=Distance("location", origin)).order_by("-is_boosted", "distance")
        return qs.order_by("-is_boosted", "-created_at")

    @staticmethod
    def _parse_point(lat, lon):
        try:
            return Point(float(lon), float(lat), srid=4326)
        except (TypeError, ValueError):
            return None

    def get_template_names(self):
        if self.request.headers.get("HX-Request"):
            return ["professionals/_search_results.html"]
        return [self.template_name]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories"] = ServiceCategory.objects.filter(is_active=True)
        context["selected_category"] = self.request.GET.get("categoria", "")
        context["lat"] = self.request.GET.get("lat", "")
        context["lon"] = self.request.GET.get("lon", "")

        user = self.request.user
        if user.is_authenticated and hasattr(user, "client_profile"):
            context["favorite_ids"] = set(
                user.client_profile.favorites.values_list("professional_id", flat=True)
            )
        return context
