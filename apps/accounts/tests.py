import re
from urllib.parse import urlsplit

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.urls import reverse


class UserModelSanityTest(TestCase):
    def test_custom_user_model_is_active(self):
        User = get_user_model()
        self.assertEqual(User.__name__, "User")

    def test_create_user_hits_the_database(self):
        User = get_user_model()
        user = User.objects.create_user(username="teste", email="teste@example.com", password="senha-forte-123")
        self.assertTrue(User.objects.filter(pk=user.pk).exists())


class SignupLoginLogoutFlowTest(TestCase):
    def test_signup_sends_verification_then_verified_user_can_login_and_logout(self):
        response = self.client.post(
            reverse("account_signup"),
            {
                "email": "nova@example.com",
                "password1": "senha-forte-123",
                "password2": "senha-forte-123",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)

        confirm_url = re.search(r"http://\S+", mail.outbox[0].body).group(0).rstrip(".")
        confirm_path = urlsplit(confirm_url).path
        response = self.client.post(confirm_path)
        self.assertEqual(response.status_code, 302)

        response = self.client.post(
            reverse("account_login"),
            {"login": "nova@example.com", "password": "senha-forte-123"},
        )
        self.assertRedirects(response, "/perfil/")

        response = self.client.post(reverse("account_logout"))
        self.assertEqual(response.status_code, 302)
