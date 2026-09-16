import json
import re
from urllib.parse import urlsplit

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.urls import reverse

from . import notifications
from .models import NotificationLog, NotificationPreference, PushSubscription


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


class NotificationPreferenceTest(TestCase):
    def test_for_user_creates_default_preference_enabled_on_all_channels(self):
        User = get_user_model()
        user = User.objects.create_user(username="u1", email="u1@example.com", password="senha-forte-123")
        preference = NotificationPreference.for_user(user)
        self.assertTrue(preference.push_enabled)
        self.assertTrue(preference.whatsapp_enabled)
        self.assertTrue(preference.email_enabled)

    def test_user_can_disable_a_single_channel_via_view(self):
        User = get_user_model()
        user = User.objects.create_user(username="u2", email="u2@example.com", password="senha-forte-123")
        self.client.force_login(user)

        response = self.client.post(
            reverse("notification-preferences"),
            {"whatsapp_enabled": ""},  # push_enabled/email_enabled ausentes = desmarcados também; só testamos 1 aqui
        )
        self.assertEqual(response.status_code, 302)
        preference = NotificationPreference.for_user(user)
        self.assertFalse(preference.whatsapp_enabled)


class NotificationChannelTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="dest", email="dest@example.com", password="senha-forte-123", phone_number="+5511999999999"
        )

    def test_email_notification_is_sent_when_enabled(self):
        notifications.send_email_notification(self.user, "Assunto", "Corpo", "test.event")
        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue(NotificationLog.objects.filter(user=self.user, channel="email", status="sent").exists())

    def test_email_notification_is_skipped_when_disabled(self):
        preference = NotificationPreference.for_user(self.user)
        preference.email_enabled = False
        preference.save()
        notifications.send_email_notification(self.user, "Assunto", "Corpo", "test.event")
        self.assertEqual(len(mail.outbox), 0)
        self.assertTrue(NotificationLog.objects.filter(user=self.user, channel="email", status="skipped").exists())

    def test_push_notification_is_skipped_without_subscription(self):
        notifications.send_push_notification(self.user, "Título", "Corpo", "test.event")
        self.assertTrue(NotificationLog.objects.filter(user=self.user, channel="push", status="skipped").exists())

    def test_push_notification_is_skipped_without_vapid_even_with_subscription(self):
        PushSubscription.objects.create(
            user=self.user, endpoint="https://push.example.com/x", p256dh="a", auth="b"
        )
        notifications.send_push_notification(self.user, "Título", "Corpo", "test.event")
        log = NotificationLog.objects.filter(user=self.user, channel="push").latest("created_at")
        self.assertEqual(log.status, "skipped")
        self.assertIn("VAPID", log.detail)

    def test_whatsapp_notification_is_skipped_without_twilio_credentials(self):
        notifications.send_whatsapp_notification(self.user, "Corpo", "test.event")
        log = NotificationLog.objects.filter(user=self.user, channel="whatsapp").latest("created_at")
        self.assertEqual(log.status, "skipped")

    def test_whatsapp_notification_is_skipped_without_phone_number(self):
        User = get_user_model()
        user_no_phone = User.objects.create_user(username="semtel", email="semtel@example.com", password="senha-forte-123")
        notifications.send_whatsapp_notification(user_no_phone, "Corpo", "test.event")
        self.assertTrue(
            NotificationLog.objects.filter(user=user_no_phone, channel="whatsapp", status="skipped").exists()
        )

    def test_dispatch_notification_queues_push_and_email_but_not_whatsapp_when_not_urgent(self):
        notifications.dispatch_notification(self.user, "test.event", "Título", "Corpo", urgent=False)
        self.assertTrue(NotificationLog.objects.filter(user=self.user, channel="push").exists())
        self.assertTrue(NotificationLog.objects.filter(user=self.user, channel="email").exists())
        self.assertFalse(NotificationLog.objects.filter(user=self.user, channel="whatsapp").exists())

    def test_dispatch_notification_also_uses_whatsapp_when_urgent(self):
        notifications.dispatch_notification(self.user, "test.event", "Título", "Corpo", urgent=True)
        self.assertTrue(NotificationLog.objects.filter(user=self.user, channel="whatsapp").exists())


class PushSubscriptionCreateViewTest(TestCase):
    def test_authenticated_user_can_register_subscription(self):
        User = get_user_model()
        user = User.objects.create_user(username="sub1", email="sub1@example.com", password="senha-forte-123")
        self.client.force_login(user)

        response = self.client.post(
            reverse("push-subscribe"),
            data=json.dumps(
                {
                    "endpoint": "https://push.example.com/abc",
                    "keys": {"p256dh": "chave-p256dh", "auth": "chave-auth"},
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(PushSubscription.objects.filter(user=user, endpoint="https://push.example.com/abc").exists())
