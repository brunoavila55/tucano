from datetime import timedelta

from asgiref.sync import async_to_sync
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone

from apps.clients.models import ClientProfile
from apps.professionals.models import ProfessionalProfile, ServiceCategory
from apps.requests import services as request_services
from apps.requests.models import Interest, ServiceRequest

from . import services
from .models import Block, Conversation, Message
from .routing import websocket_urlpatterns


class _FixedUserMiddleware:
    """Substitui o AuthMiddlewareStack em teste: injeta um usuário fixo no scope."""

    def __init__(self, app, user):
        self.app = app
        self.user = user

    async def __call__(self, scope, receive, send):
        scope["user"] = self.user
        return await self.app(scope, receive, send)


def make_selected_interest():
    User = get_user_model()
    category = ServiceCategory.objects.create(name="Categoria chat teste")

    client_user = User.objects.create_user(username="cliente_chat", email="cliente_chat@example.com", password="senha-forte-123")
    client_profile = ClientProfile.objects.create(user=client_user)

    pro_user = User.objects.create_user(username="pro_chat", email="pro_chat@example.com", password="senha-forte-123")
    professional_profile = ProfessionalProfile.objects.create(user=pro_user, main_category=category)

    service_request = ServiceRequest.objects.create(
        client=client_profile,
        category=category,
        title="Chamado para chat",
        description="Descrição",
        positions_count=1,
        scheduled_start=timezone.now() + timedelta(days=2),
        interest_window=ServiceRequest.InterestWindow.TWO_HOURS,
    )
    interest = Interest.objects.create(service_request=service_request, professional=professional_profile)
    request_services.select_interest(interest, client_user)
    return interest


class ConversationCreationTest(TestCase):
    def test_selecting_interest_creates_conversation(self):
        interest = make_selected_interest()
        self.assertTrue(Conversation.objects.filter(interest=interest).exists())


class SendMessageServiceTest(TestCase):
    def setUp(self):
        interest = make_selected_interest()
        self.conversation = interest.conversation
        self.client_user = self.conversation.client_user
        self.professional_user = self.conversation.professional_user

    def test_participant_can_send_message(self):
        message = services.send_message(self.conversation, self.client_user, "Olá!")
        self.assertEqual(message.body, "Olá!")

    def test_blocked_sender_cannot_send_message(self):
        Block.objects.create(blocker=self.professional_user, blocked=self.client_user)
        with self.assertRaises(ValidationError):
            services.send_message(self.conversation, self.client_user, "Oi?")

    def test_rate_limit_blocks_after_threshold(self):
        for i in range(services.MAX_MESSAGES_PER_MINUTE):
            services.send_message(self.conversation, self.client_user, f"mensagem {i}")
        with self.assertRaises(ValidationError):
            services.send_message(self.conversation, self.client_user, "mensagem excedente")


class ConversationViewPermissionTest(TestCase):
    def setUp(self):
        self.interest = make_selected_interest()
        self.conversation = self.interest.conversation

        User = get_user_model()
        self.outsider = User.objects.create_user(username="fora", email="fora@example.com", password="senha-forte-123")

    def test_participant_can_view_conversation(self):
        self.client.force_login(self.conversation.client_user)
        response = self.client.get(reverse("chat:detail", args=[self.interest.pk]))
        self.assertEqual(response.status_code, 200)

    def test_outsider_cannot_view_conversation(self):
        self.client.force_login(self.outsider)
        response = self.client.get(reverse("chat:detail", args=[self.interest.pk]))
        self.assertEqual(response.status_code, 403)

    def test_blocking_prevents_future_messages(self):
        self.client.force_login(self.conversation.client_user)
        self.client.post(reverse("chat:block", args=[self.interest.pk]))
        self.assertTrue(
            Block.objects.filter(
                blocker=self.conversation.client_user, blocked=self.conversation.professional_user
            ).exists()
        )
        with self.assertRaises(ValidationError):
            services.send_message(self.conversation, self.conversation.professional_user, "oi")


class ChatConsumerRealtimeTest(TransactionTestCase):
    def test_message_is_broadcast_to_both_participants_in_real_time(self):
        async_to_sync(self._scenario)()

    async def _scenario(self):
        from channels.db import database_sync_to_async

        interest = await database_sync_to_async(make_selected_interest)()
        conversation = await database_sync_to_async(lambda: interest.conversation)()
        client_user = await database_sync_to_async(lambda: conversation.client_user)()
        professional_user = await database_sync_to_async(lambda: conversation.professional_user)()

        application_for_client = _FixedUserMiddleware(URLRouter(websocket_urlpatterns), client_user)
        application_for_pro = _FixedUserMiddleware(URLRouter(websocket_urlpatterns), professional_user)

        path = f"/ws/chat/{conversation.pk}/"
        comm_client = WebsocketCommunicator(application_for_client, path)
        comm_pro = WebsocketCommunicator(application_for_pro, path)

        connected_client, _ = await comm_client.connect()
        connected_pro, _ = await comm_pro.connect()
        self.assertTrue(connected_client)
        self.assertTrue(connected_pro)

        await comm_client.send_to(text_data='{"message": "Oi, tudo bem?"}')

        response_client = await comm_client.receive_json_from()
        response_pro = await comm_pro.receive_json_from()

        self.assertEqual(response_client["body"], "Oi, tudo bem?")
        self.assertEqual(response_pro["body"], "Oi, tudo bem?")
        self.assertEqual(response_pro["sender"], client_user.get_username())

        await comm_client.disconnect()
        await comm_pro.disconnect()

    def test_outsider_cannot_connect(self):
        async_to_sync(self._outsider_scenario)()

    async def _outsider_scenario(self):
        from channels.db import database_sync_to_async

        interest = await database_sync_to_async(make_selected_interest)()
        conversation = await database_sync_to_async(lambda: interest.conversation)()

        User = get_user_model()
        outsider = await database_sync_to_async(
            lambda: User.objects.create_user(username="fora_ws", email="fora_ws@example.com", password="senha-forte-123")
        )()

        application = _FixedUserMiddleware(URLRouter(websocket_urlpatterns), outsider)
        communicator = WebsocketCommunicator(application, f"/ws/chat/{conversation.pk}/")
        connected, _ = await communicator.connect()
        self.assertFalse(connected)
