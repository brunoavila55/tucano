from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.clients.models import ClientProfile
from apps.moderation.models import AuditEvent
from apps.professionals.models import ProfessionalProfile, ServiceCategory

from . import services
from .models import Interest, ServiceRequest


def make_client(username="contratante", email=None):
    User = get_user_model()
    user = User.objects.create_user(username=username, email=email or f"{username}@example.com", password="senha-forte-123")
    return ClientProfile.objects.create(user=user)


def make_professional(username="profissional", email=None, category=None):
    User = get_user_model()
    user = User.objects.create_user(username=username, email=email or f"{username}@example.com", password="senha-forte-123")
    return ProfessionalProfile.objects.create(user=user, main_category=category)


class ServiceRequestCreationTest(TestCase):
    def setUp(self):
        self.client_profile = make_client()
        self.category = ServiceCategory.objects.create(name="Garçom de teste")

    def _build(self, **overrides):
        data = dict(
            client=self.client_profile,
            category=self.category,
            title="Preciso de um garçom",
            description="Evento hoje à noite",
            positions_count=1,
            scheduled_start=timezone.now() + timedelta(days=5),
            interest_window=ServiceRequest.InterestWindow.TWO_HOURS,
        )
        data.update(overrides)
        return ServiceRequest(**data)

    def test_each_predefined_window_can_be_used(self):
        for window in ServiceRequest.InterestWindow.values:
            with self.subTest(window=window):
                sr = self._build(
                    title=f"Chamado {window}",
                    category=ServiceCategory.objects.create(name=f"Categoria {window}"),
                    interest_window=window,
                    scheduled_start=timezone.now() + timedelta(days=10),
                )
                sr.save()
                expected_expiry = sr.published_at + ServiceRequest.WINDOW_DURATIONS[window]
                self.assertEqual(sr.expires_at, expected_expiry)

    def test_window_that_would_exceed_scheduled_start_is_rejected(self):
        sr = self._build(
            scheduled_start=timezone.now() + timedelta(minutes=30),
            interest_window=ServiceRequest.InterestWindow.ONE_DAY,
        )
        with self.assertRaises(ValidationError):
            sr.save()

    def test_duplicate_open_request_same_category_is_blocked(self):
        self._build().save()
        with self.assertRaises(ValidationError):
            self._build(title="Outro chamado igual").save()

    def test_publish_via_view_creates_audit_event(self):
        User = get_user_model()
        user = User.objects.create_user(username="c2", email="c2@example.com", password="senha-forte-123")
        ClientProfile.objects.create(user=user)
        self.client.force_login(user)

        response = self.client.post(
            reverse("requests:create"),
            {
                "category": self.category.pk,
                "title": "Preciso de DJ",
                "description": "Festa de aniversário",
                "positions_count": 1,
                "scheduled_start": (timezone.now() + timedelta(days=3)).strftime("%Y-%m-%dT%H:%M"),
                "interest_window": ServiceRequest.InterestWindow.TWO_HOURS,
                "location_label": "Centro",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(ServiceRequest.objects.filter(title="Preciso de DJ").exists())
        self.assertTrue(AuditEvent.objects.filter(event_type="service_request.published").exists())


class InterestFlowTest(TestCase):
    def setUp(self):
        self.category = ServiceCategory.objects.create(name="Bartender de teste")
        self.client_profile = make_client()
        self.request = ServiceRequest.objects.create(
            client=self.client_profile,
            category=self.category,
            title="Preciso de 2 bartenders",
            description="Evento",
            positions_count=2,
            scheduled_start=timezone.now() + timedelta(days=2),
            interest_window=ServiceRequest.InterestWindow.TWO_HOURS,
        )

    def test_professional_can_apply(self):
        pro = make_professional("p1", category=self.category)
        interest = Interest.objects.create(service_request=self.request, professional=pro, message="Posso ajudar")
        self.assertEqual(interest.status, Interest.Status.APPLIED)

    def test_professional_cannot_apply_twice(self):
        pro = make_professional("p1", category=self.category)
        Interest.objects.create(service_request=self.request, professional=pro)
        with self.assertRaises(ValidationError):
            Interest.objects.create(service_request=self.request, professional=pro)

    def test_cannot_apply_to_a_closed_request(self):
        self.request.status = ServiceRequest.Status.CANCELLED
        self.request.save(update_fields=["status"])
        pro = make_professional("p1", category=self.category)
        with self.assertRaises(ValidationError):
            Interest.objects.create(service_request=self.request, professional=pro)

    def test_selecting_one_of_two_positions_keeps_request_partially_filled_and_others_untouched(self):
        pro1 = make_professional("p1", category=self.category)
        pro2 = make_professional("p2", category=self.category)
        i1 = Interest.objects.create(service_request=self.request, professional=pro1)
        i2 = Interest.objects.create(service_request=self.request, professional=pro2)

        services.select_interest(i1, self.client_profile.user)

        self.request.refresh_from_db()
        i2.refresh_from_db()
        self.assertEqual(self.request.status, ServiceRequest.Status.PARTIALLY_FILLED)
        self.assertEqual(i2.status, Interest.Status.APPLIED)  # posição restante continua em aberto

    def test_filling_all_positions_marks_request_filled_and_rejects_remaining(self):
        pro1 = make_professional("p1", category=self.category)
        pro2 = make_professional("p2", category=self.category)
        pro3 = make_professional("p3", category=self.category)
        i1 = Interest.objects.create(service_request=self.request, professional=pro1)
        i2 = Interest.objects.create(service_request=self.request, professional=pro2)
        i3 = Interest.objects.create(service_request=self.request, professional=pro3)

        services.select_interest(i1, self.client_profile.user)
        services.select_interest(i2, self.client_profile.user)

        self.request.refresh_from_db()
        i3.refresh_from_db()
        self.assertEqual(self.request.status, ServiceRequest.Status.FILLED)
        self.assertEqual(i3.status, Interest.Status.NOT_SELECTED)

        with self.assertRaises(ValidationError):
            services.select_interest(i3, self.client_profile.user)

    def test_withdraw_interest(self):
        pro = make_professional("p1", category=self.category)
        interest = Interest.objects.create(service_request=self.request, professional=pro)
        services.withdraw_interest(interest, pro.user)
        interest.refresh_from_db()
        self.assertEqual(interest.status, Interest.Status.WITHDRAWN)

    def test_close_request_now_with_partial_selection(self):
        pro1 = make_professional("p1", category=self.category)
        pro2 = make_professional("p2", category=self.category)
        i1 = Interest.objects.create(service_request=self.request, professional=pro1)
        i2 = Interest.objects.create(service_request=self.request, professional=pro2)
        services.select_interest(i1, self.client_profile.user)

        services.close_request_now(self.request, self.client_profile.user)

        self.request.refresh_from_db()
        i2.refresh_from_db()
        self.assertEqual(self.request.status, ServiceRequest.Status.PARTIALLY_FILLED)
        self.assertEqual(i2.status, Interest.Status.NOT_SELECTED)
        self.assertIsNotNone(self.request.closed_at)

    def test_close_request_now_without_any_selection_becomes_expired(self):
        pro = make_professional("p1", category=self.category)
        interest = Interest.objects.create(service_request=self.request, professional=pro)
        services.close_request_now(self.request, self.client_profile.user)
        self.request.refresh_from_db()
        interest.refresh_from_db()
        self.assertEqual(self.request.status, ServiceRequest.Status.EXPIRED)
        self.assertEqual(interest.status, Interest.Status.EXPIRED)

    def test_cancel_request_with_reason(self):
        services.cancel_request(self.request, self.client_profile.user, "Evento cancelado pelo cliente")
        self.request.refresh_from_db()
        self.assertEqual(self.request.status, ServiceRequest.Status.CANCELLED)
        self.assertEqual(self.request.cancel_reason, "Evento cancelado pelo cliente")

    def test_audit_events_are_recorded(self):
        pro = make_professional("p1", category=self.category)
        interest = Interest.objects.create(service_request=self.request, professional=pro)
        services.select_interest(interest, self.client_profile.user)
        self.assertTrue(AuditEvent.objects.filter(event_type="interest.selected").exists())


class ExpireDueRequestsTest(TestCase):
    def setUp(self):
        self.category = ServiceCategory.objects.create(name="Fotógrafo de teste")
        self.client_profile = make_client()

    def _make_request(self, positions=1):
        sr = ServiceRequest.objects.create(
            client=self.client_profile,
            category=self.category,
            title="Chamado de teste",
            description="Descrição",
            positions_count=positions,
            scheduled_start=timezone.now() + timedelta(days=5),
            interest_window=ServiceRequest.InterestWindow.TWO_HOURS,
        )
        # Força a janela a já ter expirado, sem passar pela validação de save().
        ServiceRequest.objects.filter(pk=sr.pk).update(expires_at=timezone.now() - timedelta(minutes=1))
        sr.refresh_from_db()
        return sr

    def test_request_with_no_interest_expires(self):
        sr = self._make_request()
        expired_count = services.expire_due_requests()
        sr.refresh_from_db()
        self.assertEqual(expired_count, 1)
        self.assertEqual(sr.status, ServiceRequest.Status.EXPIRED)

    def test_request_with_partial_selection_becomes_partially_filled_on_expiry(self):
        sr = self._make_request(positions=2)
        pro1 = make_professional("p1", category=self.category)
        pro2 = make_professional("p2", category=self.category)
        i1 = Interest.objects.create(service_request=sr, professional=pro1)
        i2 = Interest.objects.create(service_request=sr, professional=pro2)
        # Seleciona antes de forçar a expiração (fluxo real: seleção acontece durante a janela).
        Interest.objects.filter(pk=i1.pk).update(status=Interest.Status.SELECTED)
        ServiceRequest.objects.filter(pk=sr.pk).update(status=ServiceRequest.Status.PARTIALLY_FILLED)

        services.expire_due_requests()

        sr.refresh_from_db()
        i2.refresh_from_db()
        self.assertEqual(sr.status, ServiceRequest.Status.PARTIALLY_FILLED)
        self.assertEqual(i2.status, Interest.Status.NOT_SELECTED)

    def test_only_due_requests_are_affected(self):
        due = self._make_request()
        not_due = ServiceRequest.objects.create(
            client=self.client_profile,
            category=ServiceCategory.objects.create(name="Categoria não expirada"),
            title="Ainda dentro da janela",
            description="Descrição",
            positions_count=1,
            scheduled_start=timezone.now() + timedelta(days=5),
            interest_window=ServiceRequest.InterestWindow.THREE_DAYS,
        )
        services.expire_due_requests()
        due.refresh_from_db()
        not_due.refresh_from_db()
        self.assertEqual(due.status, ServiceRequest.Status.EXPIRED)
        self.assertEqual(not_due.status, ServiceRequest.Status.OPEN)
