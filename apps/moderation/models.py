from django.conf import settings
from django.db import models


class AuditEvent(models.Model):
    """Trilha de auditoria para fluxos sensíveis (AGENTS.md — Entidades conceituais).

    Cobre publicação, interesse, seleção, retirada, expiração e cancelamento
    de chamados, entre outros eventos sensíveis futuros (verificação,
    moderação, assinatura).
    """

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="Nulo quando o evento é disparado pelo sistema (ex.: expiração automática).",
    )
    event_type = models.CharField(max_length=80)
    object_repr = models.CharField(max_length=255)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.event_type}: {self.object_repr}"


class ModerationCase(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Aberto"
        UNDER_REVIEW = "under_review", "Em análise"
        DECIDED = "decided", "Decidido"
        APPEALED = "appealed", "Em recurso"
        CLOSED = "closed", "Encerrado"

    class Decision(models.TextChoices):
        NONE = "none", "Sem decisão"
        DISMISSED = "dismissed", "Arquivado (sem violação)"
        WARNING = "warning", "Advertência"
        SUSPENSION = "suspension", "Suspensão de conta"

    class AppealDecision(models.TextChoices):
        PENDING = "pending", "Pendente"
        APPROVED = "approved", "Aprovado"
        REJECTED = "rejected", "Rejeitado"

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="moderation_cases_reported",
    )
    reported_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="moderation_cases_against"
    )
    reason = models.TextField()
    context_repr = models.CharField(max_length=255, blank=True)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    decision = models.CharField(max_length=20, choices=Decision.choices, default=Decision.NONE)
    decision_notes = models.TextField(blank=True)

    appeal_reason = models.TextField(blank=True)
    appeal_decision = models.CharField(max_length=20, choices=AppealDecision.choices, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    appeal_decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Denúncia contra {self.reported_user} ({self.get_status_display()})"


class Verification(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pendente"
        APPROVED = "approved", "Aprovada"
        REJECTED = "rejected", "Rejeitada"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="verifications")
    document = models.FileField(upload_to="verification_documents/")
    # Finalidade fixa e clara (não é texto livre do usuário) — consentimento
    # é dado explicitamente no formulário de solicitação.
    purpose = models.CharField(max_length=150)
    consent_given_at = models.DateTimeField(auto_now_add=True)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verifications_reviewed",
    )

    class Meta:
        ordering = ["-consent_given_at"]

    def __str__(self):
        return f"Verificação de {self.user} — {self.get_status_display()}"
