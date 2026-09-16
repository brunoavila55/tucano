from django.contrib.auth import get_user_model
from django.test import TestCase


class UserModelSanityTest(TestCase):
    def test_custom_user_model_is_active(self):
        User = get_user_model()
        self.assertEqual(User.__name__, "User")

    def test_create_user_hits_the_database(self):
        User = get_user_model()
        user = User.objects.create_user(username="teste", email="teste@example.com", password="senha-forte-123")
        self.assertTrue(User.objects.filter(pk=user.pk).exists())
