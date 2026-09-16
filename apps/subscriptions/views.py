import json
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView, View

from apps.accounts.mixins import ProfessionalRequiredMixin

from . import gateway
from .models import Boost, Subscription


class PlanView(LoginRequiredMixin, TemplateView):
    template_name = "subscriptions/plan.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["subscription"] = Subscription.for_user(self.request.user)
        context["mercadopago_configured"] = gateway.is_configured()
        return context


class SubscribeView(LoginRequiredMixin, View):
    def post(self, request):
        if not gateway.is_configured():
            messages.error(request, "Assinatura Premium indisponível no momento (pagamento não configurado).")
            return redirect("subscriptions:plan")

        back_url = request.build_absolute_uri(reverse("subscriptions:plan"))
        try:
            init_point = gateway.create_checkout_preapproval(request.user, back_url)
        except RuntimeError as exc:
            messages.error(request, str(exc))
            return redirect("subscriptions:plan")
        return redirect(init_point)


class CancelSubscriptionView(LoginRequiredMixin, View):
    def post(self, request):
        subscription = Subscription.for_user(request.user)
        gateway.cancel_preapproval(subscription)
        messages.success(request, "Assinatura cancelada.")
        return redirect("subscriptions:plan")


@method_decorator(csrf_exempt, name="dispatch")
class MercadoPagoWebhookView(View):
    def post(self, request):
        try:
            payload = json.loads(request.body or b"{}")
        except json.JSONDecodeError:
            return JsonResponse({"error": "payload inválido"}, status=400)
        gateway.handle_webhook(payload.get("data", payload))
        return JsonResponse({"status": "ok"})


class BoostActivateView(ProfessionalRequiredMixin, View):
    """Boost incluso no plano Premium (AGENTS.md — benefícios do profissional Premium)."""

    def post(self, request):
        subscription = Subscription.for_user(request.user)
        if not subscription.is_premium:
            messages.error(request, "O boost é um benefício do plano Premium.")
            return redirect("subscriptions:plan")

        Boost.objects.create(
            professional=request.user.professional_profile,
            starts_at=timezone.now(),
            ends_at=timezone.now() + timedelta(days=7),
        )
        messages.success(request, "Destaque ativado por 7 dias.")
        return redirect("subscriptions:plan")
