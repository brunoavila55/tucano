from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.generic import DetailView, View

from apps.requests.models import Interest

from . import services
from .forms import ContestReviewForm, ReviewForm
from .models import Review, ServiceConfirmation


class ConfirmationDetailView(LoginRequiredMixin, DetailView):
    template_name = "reviews/confirmation_detail.html"
    context_object_name = "confirmation"

    def get_object(self, queryset=None):
        interest = get_object_or_404(Interest, pk=self.kwargs["interest_id"], status=Interest.Status.SELECTED)
        user = self.request.user
        if user not in (interest.service_request.client.user, interest.professional.user):
            raise PermissionDenied
        if interest.service_request.scheduled_start > timezone.now():
            raise PermissionDenied
        return services.get_or_create_confirmation(interest)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        confirmation = self.object
        interest = confirmation.interest
        user = self.request.user
        is_client = user == interest.service_request.client.user

        context["is_client"] = is_client
        context["my_confirmed"] = confirmation.client_confirmed if is_client else confirmation.professional_confirmed
        context["other_confirmed"] = (
            confirmation.professional_confirmed if is_client else confirmation.client_confirmed
        )
        context["target_user"] = interest.professional.user if is_client else interest.service_request.client.user
        context["my_review"] = Review.objects.filter(confirmation=confirmation, author=user).first()

        both_reviewed = confirmation.reviews.count() == 2
        context["other_review"] = (
            Review.objects.filter(confirmation=confirmation).exclude(author=user).first() if both_reviewed else None
        )
        context["review_form"] = ReviewForm()
        context["contest_form"] = ContestReviewForm()
        return context


class ConfirmServiceView(LoginRequiredMixin, View):
    def post(self, request, interest_id):
        interest = get_object_or_404(Interest, pk=interest_id)
        confirmation = services.get_or_create_confirmation(interest)
        occurred = request.POST.get("occurred") == "yes"
        try:
            services.confirm_service(confirmation, request.user, occurred)
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
        return redirect("reviews:confirmation-detail", interest_id=interest_id)


class ReviewCreateView(LoginRequiredMixin, View):
    def post(self, request, interest_id):
        interest = get_object_or_404(Interest, pk=interest_id)
        confirmation = get_object_or_404(ServiceConfirmation, interest=interest)
        user = request.user
        is_client = user == interest.service_request.client.user
        target = interest.professional.user if is_client else interest.service_request.client.user

        form = ReviewForm(request.POST)
        if form.is_valid():
            try:
                services.submit_review(
                    confirmation, user, target, form.cleaned_data["rating"], form.cleaned_data["comment"]
                )
            except ValidationError as exc:
                messages.error(request, " ".join(exc.messages))
        else:
            messages.error(request, "Avaliação inválida.")
        return redirect("reviews:confirmation-detail", interest_id=interest_id)


class ReviewContestView(LoginRequiredMixin, View):
    def post(self, request, pk):
        review = get_object_or_404(Review, pk=pk)
        form = ContestReviewForm(request.POST)
        if form.is_valid():
            try:
                services.contest_review(review, request.user, form.cleaned_data["reason"])
            except ValidationError as exc:
                messages.error(request, " ".join(exc.messages))
        return redirect("reviews:confirmation-detail", interest_id=review.confirmation.interest_id)
