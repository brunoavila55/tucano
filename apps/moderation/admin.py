from django.contrib import admin
from django.core.exceptions import ValidationError
from django.utils import timezone

from . import services
from .models import AuditEvent, ModerationCase, Verification


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ["created_at", "event_type", "object_repr", "actor"]
    list_filter = ["event_type"]
    search_fields = ["object_repr"]
    readonly_fields = [f.name for f in AuditEvent._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(ModerationCase)
class ModerationCaseAdmin(admin.ModelAdmin):
    list_display = ["reported_user", "reporter", "status", "decision", "created_at"]
    list_filter = ["status", "decision"]
    actions = [
        "start_review",
        "decide_dismissed",
        "decide_warning",
        "decide_suspension",
        "approve_appeal",
        "reject_appeal",
    ]

    def _run_for_each(self, request, queryset, action):
        for case in queryset:
            try:
                action(case)
            except ValidationError as exc:
                self.message_user(request, f"Caso {case.pk}: {exc}", level="warning")

    @admin.action(description="Iniciar análise")
    def start_review(self, request, queryset):
        self._run_for_each(request, queryset, lambda case: services.start_review(case, request.user))

    @admin.action(description="Decidir: arquivar (sem violação)")
    def decide_dismissed(self, request, queryset):
        self._run_for_each(
            request, queryset, lambda case: services.decide_case(case, request.user, ModerationCase.Decision.DISMISSED)
        )

    @admin.action(description="Decidir: advertência")
    def decide_warning(self, request, queryset):
        self._run_for_each(
            request, queryset, lambda case: services.decide_case(case, request.user, ModerationCase.Decision.WARNING)
        )

    @admin.action(description="Decidir: suspender conta")
    def decide_suspension(self, request, queryset):
        self._run_for_each(
            request, queryset, lambda case: services.decide_case(case, request.user, ModerationCase.Decision.SUSPENSION)
        )

    @admin.action(description="Recurso: aprovar (reverte suspensão)")
    def approve_appeal(self, request, queryset):
        self._run_for_each(request, queryset, lambda case: services.resolve_appeal(case, request.user, approved=True))

    @admin.action(description="Recurso: rejeitar")
    def reject_appeal(self, request, queryset):
        self._run_for_each(request, queryset, lambda case: services.resolve_appeal(case, request.user, approved=False))


@admin.register(Verification)
class VerificationAdmin(admin.ModelAdmin):
    list_display = ["user", "purpose", "status", "consent_given_at", "reviewed_at"]
    list_filter = ["status"]
    actions = ["approve", "reject"]

    @admin.action(description="Aprovar verificação")
    def approve(self, request, queryset):
        queryset.update(status=Verification.Status.APPROVED, reviewed_at=timezone.now(), reviewed_by=request.user)

    @admin.action(description="Rejeitar verificação")
    def reject(self, request, queryset):
        queryset.update(status=Verification.Status.REJECTED, reviewed_at=timezone.now(), reviewed_by=request.user)
