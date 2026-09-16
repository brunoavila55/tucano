from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Identidade e autenticação (AGENTS.md — Entidades conceituais).

    Perfil profissional e de contratante vivem em apps.professionals/
    apps.clients, ligados a este User (Etapa 1). phone_number existe aqui
    porque é dado de contato da identidade, usado pelo canal WhatsApp/SMS
    (Etapa 5) — nunca exposto em listagens públicas.
    """

    phone_number = models.CharField(max_length=20, blank=True)


class NotificationPreference(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notification_preference"
    )
    push_enabled = models.BooleanField(default=True)
    whatsapp_enabled = models.BooleanField(default=True)
    email_enabled = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    @classmethod
    def for_user(cls, user):
        preference, _ = cls.objects.get_or_create(user=user)
        return preference

    def __str__(self):
        return f"Preferências de {self.user}"


class PushSubscription(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="push_subscriptions")
    endpoint = models.URLField(max_length=500, unique=True)
    p256dh = models.CharField(max_length=255)
    auth = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Push de {self.user}"


class NotificationLog(models.Model):
    class Channel(models.TextChoices):
        PUSH = "push", "Push"
        WHATSAPP = "whatsapp", "WhatsApp/SMS"
        EMAIL = "email", "E-mail"

    class Status(models.TextChoices):
        SENT = "sent", "Enviado"
        FAILED = "failed", "Falhou"
        SKIPPED = "skipped", "Não enviado"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notification_logs")
    channel = models.CharField(max_length=20, choices=Channel.choices)
    event_type = models.CharField(max_length=60)
    status = models.CharField(max_length=20, choices=Status.choices)
    detail = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.channel}/{self.event_type} → {self.user}: {self.status}"
