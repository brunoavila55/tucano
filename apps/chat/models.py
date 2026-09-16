from django.conf import settings
from django.db import models


class Conversation(models.Model):
    interest = models.OneToOneField(
        "requests.Interest", on_delete=models.CASCADE, related_name="conversation"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def client_user(self):
        return self.interest.service_request.client.user

    @property
    def professional_user(self):
        return self.interest.professional.user

    def other_party(self, user):
        return self.professional_user if user == self.client_user else self.client_user

    def __str__(self):
        return f"Conversa sobre {self.interest.service_request}"


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    body = models.CharField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.sender}: {self.body[:30]}"


class Block(models.Model):
    blocker = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="blocks_made")
    blocked = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="blocks_received"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["blocker", "blocked"], name="unique_block"),
        ]

    def __str__(self):
        return f"{self.blocker} bloqueou {self.blocked}"
