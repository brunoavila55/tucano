from django.core.exceptions import ValidationError
from django.utils import timezone

from .audit import log_event
from .models import ModerationCase


def open_case(reporter, reported_user, reason, context_repr=""):
    case = ModerationCase.objects.create(
        reporter=reporter, reported_user=reported_user, reason=reason, context_repr=context_repr
    )
    log_event(reporter, "moderation_case.opened", case)
    return case


def start_review(case, moderator):
    if case.status != ModerationCase.Status.OPEN:
        raise ValidationError("Este caso não está aberto para iniciar análise.")
    case.status = ModerationCase.Status.UNDER_REVIEW
    case.save(update_fields=["status"])
    log_event(moderator, "moderation_case.review_started", case)
    return case


def decide_case(case, moderator, decision, notes=""):
    if case.status not in (ModerationCase.Status.OPEN, ModerationCase.Status.UNDER_REVIEW):
        raise ValidationError("Este caso já foi decidido.")

    case.decision = decision
    case.decision_notes = notes
    case.status = ModerationCase.Status.DECIDED
    case.decided_at = timezone.now()
    case.save(update_fields=["decision", "decision_notes", "status", "decided_at"])

    if decision == ModerationCase.Decision.SUSPENSION:
        case.reported_user.is_active = False
        case.reported_user.save(update_fields=["is_active"])

    log_event(moderator, "moderation_case.decided", case, decision=decision, notes=notes)
    return case


def appeal_case(case, user, reason):
    if user != case.reported_user:
        raise ValidationError("Só a pessoa afetada pela decisão pode recorrer.")
    if case.status != ModerationCase.Status.DECIDED:
        raise ValidationError("Só é possível recorrer de um caso já decidido.")
    if case.appeal_reason:
        raise ValidationError("Este caso já tem um recurso registrado.")

    case.appeal_reason = reason
    case.appeal_decision = ModerationCase.AppealDecision.PENDING
    case.status = ModerationCase.Status.APPEALED
    case.save(update_fields=["appeal_reason", "appeal_decision", "status"])
    log_event(user, "moderation_case.appealed", case, reason=reason)
    return case


def resolve_appeal(case, moderator, approved, notes=""):
    if case.status != ModerationCase.Status.APPEALED:
        raise ValidationError("Não há recurso pendente para este caso.")

    case.appeal_decision = ModerationCase.AppealDecision.APPROVED if approved else ModerationCase.AppealDecision.REJECTED
    case.appeal_decided_at = timezone.now()
    case.status = ModerationCase.Status.CLOSED
    case.save(update_fields=["appeal_decision", "appeal_decided_at", "status"])

    if approved and case.decision == ModerationCase.Decision.SUSPENSION:
        case.reported_user.is_active = True
        case.reported_user.save(update_fields=["is_active"])

    log_event(moderator, "moderation_case.appeal_resolved", case, approved=approved, notes=notes)
    return case
