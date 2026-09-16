from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import CreateView, ListView, View

from . import services
from .forms import VERIFICATION_PURPOSE, AppealForm, ReportUserForm, VerificationRequestForm
from .models import ModerationCase, Verification


class ReportUserCreateView(LoginRequiredMixin, View):
    def post(self, request, user_id):
        reported_user = get_object_or_404(get_user_model(), pk=user_id)
        form = ReportUserForm(request.POST)
        next_url = request.POST.get("next") or reverse("home")
        if form.is_valid():
            services.open_case(
                request.user,
                reported_user,
                form.cleaned_data["reason"],
                context_repr=request.POST.get("context", ""),
            )
            messages.success(request, "Denúncia registrada. Nossa equipe vai analisar.")
        else:
            messages.error(request, "Descreva o motivo da denúncia.")
        return redirect(next_url)


class MyModerationCasesListView(LoginRequiredMixin, ListView):
    template_name = "moderation/my_cases.html"
    context_object_name = "cases"

    def get_queryset(self):
        return self.request.user.moderation_cases_against.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["appeal_form"] = AppealForm()
        return context


class AppealCaseView(LoginRequiredMixin, View):
    def post(self, request, pk):
        case = get_object_or_404(ModerationCase, pk=pk, reported_user=request.user)
        form = AppealForm(request.POST)
        if form.is_valid():
            try:
                services.appeal_case(case, request.user, form.cleaned_data["reason"])
                messages.success(request, "Recurso registrado.")
            except ValidationError as exc:
                messages.error(request, " ".join(exc.messages))
        return redirect("moderation:my-cases")


class VerificationRequestCreateView(LoginRequiredMixin, CreateView):
    model = Verification
    form_class = VerificationRequestForm
    template_name = "moderation/verification_form.html"

    def form_valid(self, form):
        form.instance.user = self.request.user
        form.instance.purpose = VERIFICATION_PURPOSE
        response = super().form_valid(form)
        messages.success(self.request, "Documento enviado. Vamos avisar quando a verificação for concluída.")
        return response

    def get_success_url(self):
        return reverse("profile-hub")
