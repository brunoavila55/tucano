from datetime import timedelta

from django.contrib.gis.db import models as gis_models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from apps.clients.models import ClientProfile
from apps.professionals.models import ProfessionalProfile, ServiceCategory


class ServiceRequest(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Rascunho"
        OPEN = "open", "Recebendo interessados"
        PARTIALLY_FILLED = "partially_filled", "Parcialmente preenchido"
        FILLED = "filled", "Preenchido"
        EXPIRED = "expired", "Expirado"
        CANCELLED = "cancelled", "Cancelado"
        COMPLETED = "completed", "Concluído"

    class InterestWindow(models.TextChoices):
        TWO_HOURS = "2h", "2 horas"
        FIVE_HOURS = "5h", "5 horas"
        ONE_DAY = "24h", "24 horas"
        THREE_DAYS = "3d", "3 dias"

    WINDOW_DURATIONS = {
        InterestWindow.TWO_HOURS: timedelta(hours=2),
        InterestWindow.FIVE_HOURS: timedelta(hours=5),
        InterestWindow.ONE_DAY: timedelta(hours=24),
        InterestWindow.THREE_DAYS: timedelta(days=3),
    }

    client = models.ForeignKey(ClientProfile, on_delete=models.CASCADE, related_name="service_requests")
    category = models.ForeignKey(ServiceCategory, on_delete=models.PROTECT, related_name="service_requests")
    title = models.CharField(max_length=150)
    description = models.TextField()
    positions_count = models.PositiveSmallIntegerField(default=1, validators=[MinValueValidator(1)])
    scheduled_start = models.DateTimeField()
    location = gis_models.PointField(geography=True, srid=4326, null=True, blank=True)
    location_label = models.CharField(max_length=150, blank=True)
    budget = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    requirements = models.TextField(blank=True)

    interest_window = models.CharField(max_length=4, choices=InterestWindow.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)

    published_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(editable=False)
    closed_at = models.DateTimeField(null=True, blank=True)
    cancel_reason = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-published_at"]

    def clean(self):
        if self.scheduled_start and self.interest_window:
            duration = self.WINDOW_DURATIONS[self.interest_window]
            if self.published_at + duration > self.scheduled_start:
                valid_labels = [
                    label
                    for value, label in self.InterestWindow.choices
                    if self.published_at + self.WINDOW_DURATIONS[value] <= self.scheduled_start
                ]
                if valid_labels:
                    raise ValidationError(
                        f"A janela de {self.get_interest_window_display()} passaria do horário do "
                        f"serviço. Opções possíveis: {', '.join(valid_labels)}."
                    )
                raise ValidationError(
                    "O horário do serviço está próximo demais para qualquer janela de interesse "
                    "disponível — escolha um horário mais distante."
                )

        if self.client_id and self.category_id:
            duplicate = ServiceRequest.objects.filter(
                client_id=self.client_id,
                category_id=self.category_id,
                status__in=[self.Status.OPEN, self.Status.PARTIALLY_FILLED],
                published_at__gte=timezone.now() - timedelta(minutes=5),
            ).exclude(pk=self.pk)
            if duplicate.exists():
                raise ValidationError(
                    "Você já tem um chamado recente e aberto para esta categoria. "
                    "Aguarde um pouco antes de publicar outro igual."
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        if not self.expires_at:
            self.expires_at = self.published_at + self.WINDOW_DURATIONS[self.interest_window]
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"


class Interest(models.Model):
    class Status(models.TextChoices):
        APPLIED = "applied", "Interesse enviado"
        SHORTLISTED = "shortlisted", "Em consideração"
        SELECTED = "selected", "Selecionado"
        NOT_SELECTED = "not_selected", "Não selecionado"
        WITHDRAWN = "withdrawn", "Retirado"
        EXPIRED = "expired", "Expirado"

    service_request = models.ForeignKey(ServiceRequest, on_delete=models.CASCADE, related_name="interests")
    professional = models.ForeignKey(ProfessionalProfile, on_delete=models.CASCADE, related_name="interests")
    message = models.CharField(max_length=280, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.APPLIED)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["service_request", "professional"], name="unique_interest_per_request"
            ),
        ]

    def clean(self):
        if self.service_request_id and self.service_request.status not in (
            ServiceRequest.Status.OPEN,
            ServiceRequest.Status.PARTIALLY_FILLED,
        ):
            raise ValidationError("Este chamado não está mais recebendo interessados.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.professional} → {self.service_request} ({self.get_status_display()})"
