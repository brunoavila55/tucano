from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.clients.models import ClientProfile
from apps.professionals.models import ProfessionalProfile, ServiceCategory
from apps.requests.models import ServiceRequest

from . import gateway
from .limits import FREE_MONTHLY_REQUEST_LIMIT, can_client_publish_request
from .models import Boost, Subscription


class SubscriptionModelTest(TestCase):
    def test_for_user_creates_default_free_active_subscription(self):
        User = get_user_model()
        user = User.objects.create_user(username="sub1", email="sub1@example.com", password="senha-forte-123")
        subscription = Subscription.for_user(user)
        self.assertEqual(subscription.plan, Subscription.Plan.FREE)
        self.assertFalse(subscription.is_premium)


class FreeRequestLimitTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="limite1", email="limite1@example.com", password="senha-forte-123")
        self.client_profile = ClientProfile.objects.create(user=self.user)

    def _publish(self, category):
        ServiceRequest.objects.create(
            client=self.client_profile,
            category=category,
            title="Chamado",
            description="Descrição",
            positions_count=1,
            scheduled_start=timezone.now() + timedelta(days=10),
            interest_window=ServiceRequest.InterestWindow.TWO_HOURS,
        )

    def test_free_client_is_blocked_after_reaching_monthly_limit(self):
        for i in range(FREE_MONTHLY_REQUEST_LIMIT):
            self._publish(ServiceCategory.objects.create(name=f"Categoria limite {i}"))

        allowed, message = can_client_publish_request(self.user)
        self.assertFalse(allowed)
        self.assertIn("Plano gratuito", message)

        with self.assertRaises(ValidationError):
            self._publish(ServiceCategory.objects.create(name="Categoria limite extra"))

    def test_premium_client_bypasses_the_limit(self):
        subscription = Subscription.for_user(self.user)
        subscription.plan = Subscription.Plan.PREMIUM
        subscription.status = Subscription.Status.ACTIVE
        subscription.save()

        for i in range(FREE_MONTHLY_REQUEST_LIMIT + 2):
            self._publish(ServiceCategory.objects.create(name=f"Categoria premium {i}"))

        self.assertEqual(ServiceRequest.objects.filter(client=self.client_profile).count(), FREE_MONTHLY_REQUEST_LIMIT + 2)


class MercadoPagoWebhookTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="mp1", email="mp1@example.com", password="senha-forte-123")

    def test_authorized_status_activates_premium(self):
        gateway.handle_webhook({"external_reference": str(self.user.pk), "status": "authorized", "id": "preap-123"})
        subscription = Subscription.for_user(self.user)
        self.assertTrue(subscription.is_premium)
        self.assertEqual(subscription.mercadopago_preapproval_id, "preap-123")

    def test_cancelled_status_deactivates_premium(self):
        subscription = Subscription.for_user(self.user)
        subscription.plan = Subscription.Plan.PREMIUM
        subscription.status = Subscription.Status.ACTIVE
        subscription.save()

        gateway.handle_webhook({"external_reference": str(self.user.pk), "status": "cancelled", "id": "preap-123"})
        subscription.refresh_from_db()
        self.assertFalse(subscription.is_premium)

    def test_unknown_external_reference_is_ignored_without_error(self):
        result = gateway.handle_webhook({"external_reference": "999999", "status": "authorized"})
        self.assertIsNone(result)

    def test_webhook_view_endpoint(self):
        response = self.client.post(
            reverse("subscriptions:mercadopago-webhook"),
            data='{"data": {"external_reference": "%s", "status": "authorized", "id": "x"}}' % self.user.pk,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Subscription.for_user(self.user).is_premium)


class SubscribeViewTest(TestCase):
    def test_subscribe_without_mercadopago_configured_shows_error_and_grants_nothing(self):
        User = get_user_model()
        user = User.objects.create_user(username="sub2", email="sub2@example.com", password="senha-forte-123")
        self.client.force_login(user)

        response = self.client.post(reverse("subscriptions:subscribe"))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Subscription.for_user(user).is_premium)

    @override_settings(MERCADOPAGO_ACCESS_TOKEN="token-teste", MERCADOPAGO_PREAPPROVAL_PLAN_ID="plan-teste")
    def test_subscribe_redirects_to_checkout_when_configured(self):
        User = get_user_model()
        user = User.objects.create_user(username="sub3", email="sub3@example.com", password="senha-forte-123")
        self.client.force_login(user)

        def fake_create_checkout_preapproval(u, back_url):
            return "https://mercadopago.example/checkout/abc"

        original = gateway.create_checkout_preapproval
        gateway.create_checkout_preapproval = fake_create_checkout_preapproval
        try:
            response = self.client.post(reverse("subscriptions:subscribe"))
        finally:
            gateway.create_checkout_preapproval = original

        self.assertRedirects(response, "https://mercadopago.example/checkout/abc", fetch_redirect_response=False)


class CancelSubscriptionViewTest(TestCase):
    def test_cancel_downgrades_to_free(self):
        User = get_user_model()
        user = User.objects.create_user(username="sub4", email="sub4@example.com", password="senha-forte-123")
        subscription = Subscription.for_user(user)
        subscription.plan = Subscription.Plan.PREMIUM
        subscription.status = Subscription.Status.ACTIVE
        subscription.save()

        self.client.force_login(user)
        response = self.client.post(reverse("subscriptions:cancel"))
        self.assertEqual(response.status_code, 302)
        subscription.refresh_from_db()
        self.assertFalse(subscription.is_premium)
        self.assertEqual(subscription.status, Subscription.Status.CANCELLED)


class BoostActivateViewTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="boost1", email="boost1@example.com", password="senha-forte-123")
        self.professional = ProfessionalProfile.objects.create(user=self.user)
        self.client.force_login(self.user)

    def test_free_professional_cannot_activate_boost(self):
        response = self.client.post(reverse("subscriptions:boost-activate"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Boost.objects.filter(professional=self.professional).count(), 0)

    def test_premium_professional_can_activate_boost(self):
        subscription = Subscription.for_user(self.user)
        subscription.plan = Subscription.Plan.PREMIUM
        subscription.status = Subscription.Status.ACTIVE
        subscription.save()

        response = self.client.post(reverse("subscriptions:boost-activate"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Boost.objects.filter(professional=self.professional).count(), 1)
