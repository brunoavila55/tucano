from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.clients.models import ClientProfile
from apps.professionals.models import ProfessionalProfile, ServiceCategory
from apps.requests import services as request_services
from apps.requests.models import Interest, ServiceRequest

from . import services
from .models import Review, ServiceConfirmation


def make_past_selected_interest():
    """Chamado cujo horário do serviço já passou, com um profissional selecionado."""
    User = get_user_model()
    category = ServiceCategory.objects.create(name="Categoria review teste")

    client_user = User.objects.create_user(username="cliente_rev", email="cliente_rev@example.com", password="senha-forte-123")
    client_profile = ClientProfile.objects.create(user=client_user)

    pro_user = User.objects.create_user(username="pro_rev", email="pro_rev@example.com", password="senha-forte-123")
    professional_profile = ProfessionalProfile.objects.create(user=pro_user, main_category=category)

    # scheduled_start no futuro para passar pela validação de publicação e
    # seleção; só depois de selecionado empurramos pro passado direto no
    # banco (bypassando o save()), simulando o tempo já ter passado.
    service_request = ServiceRequest.objects.create(
        client=client_profile,
        category=category,
        title="Chamado para avaliação",
        description="Descrição",
        positions_count=1,
        scheduled_start=timezone.now() + timedelta(hours=3),
        interest_window=ServiceRequest.InterestWindow.TWO_HOURS,
    )
    interest = Interest.objects.create(service_request=service_request, professional=professional_profile)
    request_services.select_interest(interest, client_user)

    ServiceRequest.objects.filter(pk=service_request.pk).update(
        scheduled_start=timezone.now() - timedelta(hours=1)
    )
    interest.refresh_from_db()
    return interest


class ServiceConfirmationTest(TestCase):
    def setUp(self):
        self.interest = make_past_selected_interest()
        self.client_user = self.interest.service_request.client.user
        self.professional_user = self.interest.professional.user

    def test_confirmation_created_lazily_on_first_view(self):
        self.client.force_login(self.client_user)
        response = self.client.get(reverse("reviews:confirmation-detail", args=[self.interest.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(ServiceConfirmation.objects.filter(interest=self.interest).exists())

    def test_outsider_cannot_view_confirmation(self):
        User = get_user_model()
        outsider = User.objects.create_user(username="fora_rev", email="fora_rev@example.com", password="senha-forte-123")
        confirmation = services.get_or_create_confirmation(self.interest)
        self.client.force_login(outsider)
        response = self.client.get(reverse("reviews:confirmation-detail", args=[self.interest.pk]))
        self.assertEqual(response.status_code, 403)

    def test_both_confirming_yes_makes_it_legitimate(self):
        confirmation = services.get_or_create_confirmation(self.interest)
        services.confirm_service(confirmation, self.client_user, True)
        services.confirm_service(confirmation, self.professional_user, True)
        confirmation.refresh_from_db()
        self.assertTrue(confirmation.is_legitimate)
        self.assertFalse(confirmation.has_dispute)

    def test_diverging_answers_flag_a_dispute(self):
        confirmation = services.get_or_create_confirmation(self.interest)
        services.confirm_service(confirmation, self.client_user, True)
        services.confirm_service(confirmation, self.professional_user, False)
        confirmation.refresh_from_db()
        self.assertFalse(confirmation.is_legitimate)
        self.assertTrue(confirmation.has_dispute)

    def test_create_pending_confirmations_covers_due_interest(self):
        created = services.create_pending_confirmations()
        self.assertEqual(created, 1)
        self.assertTrue(ServiceConfirmation.objects.filter(interest=self.interest).exists())

    def test_confirming_too_early_is_forbidden(self):
        User = get_user_model()
        category = ServiceCategory.objects.create(name="Categoria futura")
        client_user = User.objects.create_user(username="cliente_fut", email="cliente_fut@example.com", password="senha-forte-123")
        client_profile = ClientProfile.objects.create(user=client_user)
        pro_user = User.objects.create_user(username="pro_fut", email="pro_fut@example.com", password="senha-forte-123")
        professional_profile = ProfessionalProfile.objects.create(user=pro_user, main_category=category)
        service_request = ServiceRequest.objects.create(
            client=client_profile,
            category=category,
            title="Chamado futuro",
            description="Descrição",
            positions_count=1,
            scheduled_start=timezone.now() + timedelta(days=2),
            interest_window=ServiceRequest.InterestWindow.TWO_HOURS,
        )
        interest = Interest.objects.create(service_request=service_request, professional=professional_profile)
        request_services.select_interest(interest, client_user)

        self.client.force_login(client_user)
        response = self.client.get(reverse("reviews:confirmation-detail", args=[interest.pk]))
        self.assertEqual(response.status_code, 403)


class ReviewFlowTest(TestCase):
    def setUp(self):
        self.interest = make_past_selected_interest()
        self.client_user = self.interest.service_request.client.user
        self.professional_user = self.interest.professional.user
        self.confirmation = services.get_or_create_confirmation(self.interest)

    def test_cannot_review_without_confirmation(self):
        with self.assertRaises(ValidationError):
            services.submit_review(self.confirmation, self.client_user, self.professional_user, 5, "Ótimo!")

    def test_cannot_review_with_only_one_side_confirmed(self):
        services.confirm_service(self.confirmation, self.client_user, True)
        with self.assertRaises(ValidationError):
            services.submit_review(self.confirmation, self.client_user, self.professional_user, 5, "Ótimo!")

    def test_review_allowed_after_both_confirm(self):
        services.confirm_service(self.confirmation, self.client_user, True)
        services.confirm_service(self.confirmation, self.professional_user, True)
        review = services.submit_review(self.confirmation, self.client_user, self.professional_user, 5, "Ótimo!")
        self.assertEqual(review.rating, 5)

    def test_cannot_review_twice(self):
        services.confirm_service(self.confirmation, self.client_user, True)
        services.confirm_service(self.confirmation, self.professional_user, True)
        services.submit_review(self.confirmation, self.client_user, self.professional_user, 5, "Ótimo!")
        with self.assertRaises(ValidationError):
            services.submit_review(self.confirmation, self.client_user, self.professional_user, 1, "De novo")

    def test_other_review_hidden_until_both_submitted(self):
        services.confirm_service(self.confirmation, self.client_user, True)
        services.confirm_service(self.confirmation, self.professional_user, True)
        services.submit_review(self.confirmation, self.client_user, self.professional_user, 5, "Ótimo!")

        self.client.force_login(self.professional_user)
        response = self.client.get(reverse("reviews:confirmation-detail", args=[self.interest.pk]))
        self.assertIsNone(response.context["other_review"])

        services.submit_review(self.confirmation, self.professional_user, self.client_user, 4, "Também ótimo")
        response = self.client.get(reverse("reviews:confirmation-detail", args=[self.interest.pk]))
        self.assertIsNotNone(response.context["other_review"])


class ReviewContestTest(TestCase):
    def setUp(self):
        self.interest = make_past_selected_interest()
        self.client_user = self.interest.service_request.client.user
        self.professional_user = self.interest.professional.user
        confirmation = services.get_or_create_confirmation(self.interest)
        services.confirm_service(confirmation, self.client_user, True)
        services.confirm_service(confirmation, self.professional_user, True)
        self.review = services.submit_review(confirmation, self.client_user, self.professional_user, 1, "Ruim")

    def test_target_can_contest_review(self):
        services.contest_review(self.review, self.professional_user, "Não corresponde ao ocorrido")
        self.review.refresh_from_db()
        self.assertTrue(self.review.contested)

    def test_author_cannot_contest_own_review(self):
        with self.assertRaises(ValidationError):
            services.contest_review(self.review, self.client_user, "Motivo qualquer")

    def test_cannot_contest_twice(self):
        services.contest_review(self.review, self.professional_user, "Motivo 1")
        with self.assertRaises(ValidationError):
            services.contest_review(self.review, self.professional_user, "Motivo 2")

    def test_contest_via_view(self):
        self.client.force_login(self.professional_user)
        response = self.client.post(
            reverse("reviews:review-contest", args=[self.review.pk]), {"reason": "Discordo"}
        )
        self.assertEqual(response.status_code, 302)
        self.review.refresh_from_db()
        self.assertTrue(self.review.contested)
        self.assertEqual(self.review.contest_reason, "Discordo")
