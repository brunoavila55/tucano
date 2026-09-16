from django.contrib import messages
from django.contrib.gis.db.models.functions import Distance
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import CreateView, DetailView, FormView, ListView, View

from apps.accounts.mixins import ClientRequiredMixin, ProfessionalRequiredMixin
from apps.moderation.audit import log_event

from . import services
from .forms import CancelRequestForm, InterestForm, ServiceRequestForm
from .models import Interest, ServiceRequest


class ServiceRequestCreateView(ClientRequiredMixin, CreateView):
    model = ServiceRequest
    form_class = ServiceRequestForm
    template_name = "requests/servicerequest_form.html"

    def form_valid(self, form):
        form.instance.client = self.request.user.client_profile
        try:
            response = super().form_valid(form)
        except ValidationError as exc:
            form.add_error(None, exc)
            return self.form_invalid(form)
        log_event(self.request.user, "service_request.published", self.object)
        services.notify_compatible_professionals(self.object)
        return response

    def get_success_url(self):
        return reverse("requests:detail", args=[self.object.pk])


class ServiceRequestCompatibleListView(ProfessionalRequiredMixin, ListView):
    model = ServiceRequest
    template_name = "requests/servicerequest_list.html"
    context_object_name = "service_requests"
    paginate_by = 10

    def get_queryset(self):
        profile = self.request.user.professional_profile
        qs = ServiceRequest.objects.filter(
            status__in=[ServiceRequest.Status.OPEN, ServiceRequest.Status.PARTIALLY_FILLED],
            category=profile.main_category,
        )
        if profile.location:
            qs = qs.exclude(location__isnull=True).annotate(distance=Distance("location", profile.location))
            return qs.order_by("distance")
        return qs.order_by("-published_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        applied_ids = set(
            Interest.objects.filter(professional=self.request.user.professional_profile).values_list(
                "service_request_id", flat=True
            )
        )
        context["applied_ids"] = applied_ids
        return context


class ServiceRequestDetailView(DetailView):
    model = ServiceRequest
    template_name = "requests/servicerequest_detail.html"
    context_object_name = "service_request"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        service_request = self.object
        is_owner = user.is_authenticated and hasattr(user, "client_profile") and service_request.client_id == user.client_profile.pk
        context["is_owner"] = is_owner
        if is_owner:
            context["interests"] = service_request.interests.select_related("professional__user")
        if user.is_authenticated and hasattr(user, "professional_profile"):
            context["my_interest"] = service_request.interests.filter(
                professional=user.professional_profile
            ).first()
            context["interest_form"] = InterestForm()
        return context


class ServiceRequestInterestsPartialView(ClientRequiredMixin, DetailView):
    model = ServiceRequest
    template_name = "requests/_interests_list.html"
    context_object_name = "service_request"

    def get_queryset(self):
        return ServiceRequest.objects.filter(client=self.request.user.client_profile)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["interests"] = self.object.interests.select_related("professional__user")
        return context


class InterestCreateView(ProfessionalRequiredMixin, CreateView):
    model = Interest
    form_class = InterestForm

    def form_valid(self, form):
        service_request = get_object_or_404(ServiceRequest, pk=self.kwargs["pk"])
        form.instance.service_request = service_request
        form.instance.professional = self.request.user.professional_profile
        try:
            response = super().form_valid(form)
        except ValidationError as exc:
            messages.error(self.request, " ".join(exc.messages))
            return redirect("requests:detail", pk=service_request.pk)
        log_event(self.request.user, "interest.applied", self.object, service_request_id=service_request.pk)
        return response

    def form_invalid(self, form):
        return redirect("requests:detail", pk=self.kwargs["pk"])

    def get_success_url(self):
        return reverse("requests:detail", args=[self.kwargs["pk"]])


class InterestWithdrawView(ProfessionalRequiredMixin, View):
    def post(self, request, pk):
        interest = get_object_or_404(Interest, pk=pk, professional=request.user.professional_profile)
        try:
            services.withdraw_interest(interest, request.user)
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
        return redirect("requests:detail", pk=interest.service_request_id)


class SelectInterestView(ClientRequiredMixin, View):
    def post(self, request, pk):
        interest = get_object_or_404(Interest, pk=pk)
        if interest.service_request.client_id != request.user.client_profile.pk:
            raise PermissionDenied
        try:
            services.select_interest(interest, request.user)
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
        return redirect("requests:detail", pk=interest.service_request_id)


class EndRequestView(ClientRequiredMixin, View):
    def post(self, request, pk):
        service_request = get_object_or_404(ServiceRequest, pk=pk, client=request.user.client_profile)
        try:
            services.close_request_now(service_request, request.user)
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
        return redirect("requests:detail", pk=service_request.pk)


class CancelRequestView(ClientRequiredMixin, FormView):
    form_class = CancelRequestForm
    template_name = "requests/cancel_form.html"

    @property
    def service_request(self):
        if not hasattr(self, "_service_request"):
            self._service_request = get_object_or_404(
                ServiceRequest, pk=self.kwargs["pk"], client=self.request.user.client_profile
            )
        return self._service_request

    def form_valid(self, form):
        try:
            services.cancel_request(self.service_request, self.request.user, form.cleaned_data["reason"])
        except ValidationError as exc:
            form.add_error(None, exc)
            return self.form_invalid(form)
        return redirect("requests:detail", pk=self.service_request.pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["service_request"] = self.service_request
        return context
