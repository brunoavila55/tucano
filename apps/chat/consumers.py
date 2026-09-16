import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.core.exceptions import ValidationError

from . import services
from .models import Conversation


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.conversation_id = self.scope["url_route"]["kwargs"]["conversation_id"]
        self.group_name = f"chat_{self.conversation_id}"

        user = self.scope["user"]
        if not user.is_authenticated or not await self._user_can_access(user):
            await self.close()
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        body = (data.get("message") or "").strip()
        if not body:
            return

        user = self.scope["user"]
        try:
            message = await self._send_message(user, body)
        except ValidationError as exc:
            await self.send(text_data=json.dumps({"error": " ".join(exc.messages)}))
            return

        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "chat.message",
                "sender_id": user.id,
                "sender": user.get_username(),
                "body": message.body,
                "created_at": message.created_at.isoformat(),
            },
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def _user_can_access(self, user):
        try:
            conversation = Conversation.objects.select_related(
                "interest__service_request__client__user", "interest__professional__user"
            ).get(pk=self.conversation_id)
        except Conversation.DoesNotExist:
            return False
        return user in (conversation.client_user, conversation.professional_user)

    @database_sync_to_async
    def _send_message(self, user, body):
        conversation = Conversation.objects.get(pk=self.conversation_id)
        return services.send_message(conversation, user, body)
