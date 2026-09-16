import datetime

from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from apps.clients.models import ClientProfile

from .models import Availability, PortfolioItem, ProfessionalProfile, ServiceCategory

# GIF 1x1 válido — suficiente para o Pillow aceitar como imagem no teste.
TINY_GIF = (
    b"GIF87a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00"
    b"\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
)


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


class ServiceCategoryExclusionTest(TestCase):
    def test_excluded_category_is_blocked(self):
        with self.assertRaises(ValidationError):
            ServiceCategory.objects.create(name="Advocacia trabalhista")

    def test_allowed_category_with_class_council_is_not_blocked(self):
        category = ServiceCategory.objects.create(name="Engenharia ambiental")
        self.assertEqual(category.slug, "engenharia-ambiental")

    def test_seed_migration_populated_initial_categories(self):
        self.assertTrue(ServiceCategory.objects.filter(slug="dj").exists())
        self.assertTrue(ServiceCategory.objects.filter(slug="jardinagem").exists())


class AvailabilityValidationTest(TestCase):
    def setUp(self):
        User = get_user_model()
        user = User.objects.create_user(username="p1", email="p1@example.com", password="senha-forte-123")
        self.profile = ProfessionalProfile.objects.create(user=user)

    def test_end_time_before_start_time_is_rejected(self):
        availability = Availability(
            professional=self.profile,
            weekday=0,
            start_time=datetime.time(18, 0),
            end_time=datetime.time(10, 0),
        )
        with self.assertRaises(ValidationError):
            availability.save()

    def test_valid_availability_is_saved(self):
        availability = Availability.objects.create(
            professional=self.profile,
            weekday=0,
            start_time=datetime.time(10, 0),
            end_time=datetime.time(18, 0),
        )
        self.assertTrue(Availability.objects.filter(pk=availability.pk).exists())


class PortfolioItemTest(TestCase):
    def test_professional_can_upload_portfolio_photo(self):
        User = get_user_model()
        user = User.objects.create_user(username="p2", email="p2@example.com", password="senha-forte-123")
        profile = ProfessionalProfile.objects.create(user=user)
        self.client.force_login(user)

        response = self.client.post(
            reverse("professionals:portfolio-create"),
            {"image": SimpleUploadedFile("foto.gif", TINY_GIF, content_type="image/gif"), "caption": "Evento X"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(PortfolioItem.objects.filter(professional=profile, caption="Evento X").exists())


class ProfessionalSearchDistanceTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.category = ServiceCategory.objects.create(name="Barista de teste")

        near_user = User.objects.create_user(username="perto", email="perto@example.com", password="senha-forte-123")
        self.near = ProfessionalProfile.objects.create(
            user=near_user,
            main_category=self.category,
            location=Point(-46.6333, -23.5505, srid=4326),  # São Paulo
            location_label="São Paulo, SP",
        )

        far_user = User.objects.create_user(username="longe", email="longe@example.com", password="senha-forte-123")
        self.far = ProfessionalProfile.objects.create(
            user=far_user,
            main_category=self.category,
            location=Point(-38.5267, -3.7327, srid=4326),  # Fortaleza
            location_label="Fortaleza, CE",
        )

    def test_search_orders_by_distance_from_given_point(self):
        response = self.client.get(
            reverse("professionals:search"), {"lat": "-23.5505", "lon": "-46.6333"}
        )
        self.assertEqual(response.status_code, 200)
        results = list(response.context["professionals"])
        self.assertEqual(results[0].pk, self.near.pk)
        self.assertEqual(results[-1].pk, self.far.pk)

    def test_search_filters_by_category_across_the_country(self):
        response = self.client.get(
            reverse("professionals:search"), {"categoria": self.category.slug}
        )
        self.assertEqual(response.status_code, 200)
        pks = {p.pk for p in response.context["professionals"]}
        self.assertEqual(pks, {self.near.pk, self.far.pk})
