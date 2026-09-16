from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.clients.models import ClientProfile

from .models import ProfessionalProfile


class ProfessionalPermissionTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.professional = User.objects.create_user(
            username="profissional", email="p@example.com", password="senha-forte-123"
        )
        ProfessionalProfile.objects.create(user=self.professional)

        self.client_user = User.objects.create_user(
            username="contratante", email="c@example.com", password="senha-forte-123"
        )
        ClientProfile.objects.create(user=self.client_user)

    def test_professional_can_access_dashboard(self):
        self.client.force_login(self.professional)
        response = self.client.get(reverse("professionals:dashboard"))
        self.assertEqual(response.status_code, 200)

    def test_client_cannot_access_professional_dashboard(self):
        self.client.force_login(self.client_user)
        response = self.client.get(reverse("professionals:dashboard"))
        self.assertEqual(response.status_code, 403)

    def test_anonymous_is_redirected_to_login(self):
        response = self.client.get(reverse("professionals:dashboard"))
        self.assertEqual(response.status_code, 302)

    def test_user_can_have_both_profiles(self):
        ProfessionalProfile.objects.create(user=self.client_user)
        self.assertTrue(hasattr(self.client_user, "client_profile"))
        self.assertTrue(ProfessionalProfile.objects.filter(user=self.client_user).exists())
