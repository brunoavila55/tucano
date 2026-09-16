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
