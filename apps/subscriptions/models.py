from django.conf import settings
from django.db import models
from django.utils import timezone


class Subscription(models.Model):
    class Plan(models.TextChoices):
        FREE = "free", "Gratuito"
        PREMIUM = "premium", "Premium"

    class Status(models.TextChoices):
        ACTIVE = "active", "Ativa"
        CANCELLED = "cancelled", "Cancelada"
        PAST_DUE = "past_due", "Pagamento pendente"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="subscription")
    plan = models.CharField(max_length=20, choices=Plan.choices, default=Plan.FREE)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    mercadopago_preapproval_id = models.CharField(max_length=100, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def is_premium(self):
        return self.plan == self.Plan.PREMIUM and self.status == self.Status.ACTIVE

    @classmethod
    def for_user(cls, user):
        subscription, _ = cls.objects.get_or_create(user=user)
        return subscription

    def __str__(self):
        return f"{self.user} — {self.get_plan_display()} ({self.get_status_display()})"


class Boost(models.Model):
    """Promoção com início/fim identificados — nunca substitui compatibilidade
    (AGENTS.md: "Encontrar profissionais" e "Modelo freemium")."""

    professional = models.ForeignKey(
        "professionals.ProfessionalProfile", on_delete=models.CASCADE, related_name="boosts"
    )
    starts_at = models.DateTimeField(default=timezone.now)
    ends_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-starts_at"]

    def is_active(self, at=None):
        at = at or timezone.now()
        return self.starts_at <= at <= self.ends_at

    def __str__(self):
        return f"Boost de {self.professional} ({self.starts_at:%d/%m} a {self.ends_at:%d/%m})"
