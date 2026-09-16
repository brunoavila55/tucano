from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.professionals.models import ProfessionalProfile

from .models import ClientProfile


class ClientPermissionTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.client_user = User.objects.create_user(
            username="contratante", email="c@example.com", password="senha-forte-123"
        )
        ClientProfile.objects.create(user=self.client_user)

        self.professional = User.objects.create_user(
            username="profissional", email="p@example.com", password="senha-forte-123"
        )
        ProfessionalProfile.objects.create(user=self.professional)

    def test_client_can_access_dashboard(self):
        self.client.force_login(self.client_user)
        response = self.client.get(reverse("clients:dashboard"))
        self.assertEqual(response.status_code, 200)

    def test_professional_cannot_access_client_dashboard(self):
        self.client.force_login(self.professional)
        response = self.client.get(reverse("clients:dashboard"))
        self.assertEqual(response.status_code, 403)

    def test_anonymous_is_redirected_to_login(self):
        response = self.client.get(reverse("clients:dashboard"))
        self.assertEqual(response.status_code, 302)
