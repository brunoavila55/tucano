from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.professionals.models import ProfessionalProfile, ServiceCategory

from .models import ClientProfile, Favorite


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


class FavoriteTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.category = ServiceCategory.objects.create(name="Categoria favorito teste")

        self.client_user = User.objects.create_user(username="fav_cliente", email="fav_cliente@example.com", password="senha-forte-123")
        self.client_profile = ClientProfile.objects.create(user=self.client_user)

        pro_user = User.objects.create_user(username="fav_pro", email="fav_pro@example.com", password="senha-forte-123")
        self.professional = ProfessionalProfile.objects.create(
            user=pro_user, main_category=self.category, location_label="Centro"
        )

    def test_client_can_favorite_and_unfavorite(self):
        self.client.force_login(self.client_user)
        url = reverse("clients:favorite-toggle", args=[self.professional.pk])

        self.client.post(url)
        self.assertTrue(Favorite.objects.filter(client=self.client_profile, professional=self.professional).exists())

        self.client.post(url)
        self.assertFalse(Favorite.objects.filter(client=self.client_profile, professional=self.professional).exists())

    def test_professional_cannot_favorite(self):
        User = get_user_model()
        other_pro_user = User.objects.create_user(username="fav_pro2", email="fav_pro2@example.com", password="senha-forte-123")
        ProfessionalProfile.objects.create(user=other_pro_user)
        self.client.force_login(other_pro_user)
        response = self.client.post(reverse("clients:favorite-toggle", args=[self.professional.pk]))
        self.assertEqual(response.status_code, 403)

    def test_favorites_list_shows_only_own_favorites(self):
        Favorite.objects.create(client=self.client_profile, professional=self.professional)

        User = get_user_model()
        other_client_user = User.objects.create_user(username="outro_cliente", email="outro_cliente@example.com", password="senha-forte-123")
        ClientProfile.objects.create(user=other_client_user)

        self.client.force_login(other_client_user)
        response = self.client.get(reverse("clients:favorites"))
        self.assertEqual(len(response.context["favorites"]), 0)

        self.client.force_login(self.client_user)
        response = self.client.get(reverse("clients:favorites"))
        self.assertEqual(len(response.context["favorites"]), 1)

    def test_publish_form_is_prefilled_from_a_favorite(self):
        Favorite.objects.create(client=self.client_profile, professional=self.professional)
        self.client.force_login(self.client_user)
        response = self.client.get(reverse("requests:create") + f"?favorito={self.professional.pk}")
        self.assertEqual(response.context["form"].initial["category"], self.professional.main_category_id)
        self.assertEqual(response.context["form"].initial["location_label"], "Centro")

    def test_publish_form_ignores_favorito_id_from_another_clients_favorite(self):
        User = get_user_model()
        other_client_user = User.objects.create_user(username="outro_cliente2", email="outro_cliente2@example.com", password="senha-forte-123")
        ClientProfile.objects.create(user=other_client_user)

        self.client.force_login(other_client_user)
        response = self.client.get(reverse("requests:create") + f"?favorito={self.professional.pk}")
        self.assertNotIn("category", response.context["form"].initial)
