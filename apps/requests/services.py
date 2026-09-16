from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.accounts.notifications import dispatch_notification
from apps.chat.models import Conversation
from apps.moderation.audit import log_event
from apps.professionals.models import ProfessionalProfile

from .models import Interest, ServiceRequest

URGENT_WINDOWS = {ServiceRequest.InterestWindow.TWO_HOURS, ServiceRequest.InterestWindow.FIVE_HOURS}


def _finalize_remaining_interests(service_request, final_status, event_type, notify_body):
    interests = list(
        service_request.interests.filter(status=Interest.Status.APPLIED).select_related("professional__user")
    )
    service_request.interests.filter(status=Interest.Status.APPLIED).update(status=final_status)
    for interest in interests:
        dispatch_notification(interest.professional.user, event_type, service_request.title, notify_body)


def notify_compatible_professionals(service_request):
    """Novo chamado compatível (AGENTS.md — Notificações em camadas)."""
    urgent = service_request.interest_window in URGENT_WINDOWS
    professionals = ProfessionalProfile.objects.filter(main_category=service_request.category).select_related("user")
    title = f"Novo chamado: {service_request.title}"
    body = (
        f"{service_request.category} em {service_request.location_label or 'sua região'} — "
        f"janela de {service_request.get_interest_window_display()}."
    )
    for professional in professionals:
        dispatch_notification(professional.user, "service_request.compatible", title, body, urgent=urgent)


def select_interest(interest, actor):
    service_request = interest.service_request
    if service_request.status not in (ServiceRequest.Status.OPEN, ServiceRequest.Status.PARTIALLY_FILLED):
        raise ValidationError("Este chamado não está mais aberto para seleção.")
    if interest.status != Interest.Status.APPLIED:
        raise ValidationError("Este interesse não pode mais ser selecionado.")

    interest.status = Interest.Status.SELECTED
    interest.save(update_fields=["status"])

    selected_count = service_request.interests.filter(status=Interest.Status.SELECTED).count()
    if selected_count >= service_request.positions_count:
        service_request.status = ServiceRequest.Status.FILLED
        service_request.closed_at = timezone.now()
        _finalize_remaining_interests(
            service_request,
            Interest.Status.NOT_SELECTED,
            "interest.not_selected",
            f'Outro profissional foi escolhido para "{service_request.title}".',
        )
        service_request.save(update_fields=["status", "closed_at"])
    else:
        service_request.status = ServiceRequest.Status.PARTIALLY_FILLED
        service_request.save(update_fields=["status"])

    Conversation.objects.get_or_create(interest=interest)
    dispatch_notification(
        interest.professional.user,
        "interest.selected",
        f'Você foi selecionado para "{service_request.title}"',
        "Combine os detalhes diretamente com o contratante pelo chat.",
    )
    log_event(actor, "interest.selected", interest, service_request_id=service_request.pk)
    return interest


def withdraw_interest(interest, actor):
    if interest.status != Interest.Status.APPLIED:
        raise ValidationError("Este interesse não pode mais ser retirado.")
    interest.status = Interest.Status.WITHDRAWN
    interest.save(update_fields=["status"])
    log_event(actor, "interest.withdrawn", interest)
    return interest


def close_request_now(service_request, actor):
    """Contratante encerra manualmente, a qualquer momento, antes do fim da janela."""
    if service_request.status not in (ServiceRequest.Status.OPEN, ServiceRequest.Status.PARTIALLY_FILLED):
        raise ValidationError("Este chamado já está encerrado.")

    selected_count = service_request.interests.filter(status=Interest.Status.SELECTED).count()
    if selected_count >= service_request.positions_count and service_request.positions_count > 0:
        service_request.status = ServiceRequest.Status.FILLED
        _finalize_remaining_interests(
            service_request,
            Interest.Status.NOT_SELECTED,
            "interest.not_selected",
            f'O chamado "{service_request.title}" foi encerrado — outro profissional foi escolhido.',
        )
    elif selected_count > 0:
        service_request.status = ServiceRequest.Status.PARTIALLY_FILLED
        _finalize_remaining_interests(
            service_request,
            Interest.Status.NOT_SELECTED,
            "interest.not_selected",
            f'O chamado "{service_request.title}" foi encerrado — outro profissional foi escolhido.',
        )
    else:
        service_request.status = ServiceRequest.Status.EXPIRED
        _finalize_remaining_interests(
            service_request,
            Interest.Status.EXPIRED,
            "interest.expired",
            f'O chamado "{service_request.title}" foi encerrado sem seleção.',
        )

    service_request.closed_at = timezone.now()
    service_request.save(update_fields=["status", "closed_at"])
    log_event(actor, "service_request.closed_manually", service_request)
    return service_request


def cancel_request(service_request, actor, reason):
    if service_request.status in (ServiceRequest.Status.CANCELLED, ServiceRequest.Status.COMPLETED):
        raise ValidationError("Este chamado não pode mais ser cancelado.")
    service_request.status = ServiceRequest.Status.CANCELLED
    service_request.cancel_reason = reason
    service_request.closed_at = timezone.now()
    service_request.save(update_fields=["status", "cancel_reason", "closed_at"])
    _finalize_remaining_interests(
        service_request,
        Interest.Status.EXPIRED,
        "service_request.cancelled",
        f'O chamado "{service_request.title}" foi cancelado. Motivo: {reason}',
    )
    log_event(actor, "service_request.cancelled", service_request, reason=reason)
    return service_request


def expire_due_requests():
    """Varredura periódica (Celery beat) — expira chamados cuja janela terminou."""
    now = timezone.now()
    due = ServiceRequest.objects.filter(
        status__in=[ServiceRequest.Status.OPEN, ServiceRequest.Status.PARTIALLY_FILLED],
        expires_at__lte=now,
    )
    expired_count = 0
    for service_request in due:
        selected_count = service_request.interests.filter(status=Interest.Status.SELECTED).count()
        if selected_count >= service_request.positions_count and service_request.positions_count > 0:
            service_request.status = ServiceRequest.Status.FILLED
            _finalize_remaining_interests(
                service_request,
                Interest.Status.NOT_SELECTED,
                "interest.not_selected",
                f'O chamado "{service_request.title}" expirou — outro profissional foi escolhido.',
            )
        elif selected_count > 0:
            service_request.status = ServiceRequest.Status.PARTIALLY_FILLED
            _finalize_remaining_interests(
                service_request,
                Interest.Status.NOT_SELECTED,
                "interest.not_selected",
                f'O chamado "{service_request.title}" expirou — outro profissional foi escolhido.',
            )
        else:
            service_request.status = ServiceRequest.Status.EXPIRED
            _finalize_remaining_interests(
                service_request,
                Interest.Status.EXPIRED,
                "interest.expired",
                f'O chamado "{service_request.title}" expirou sem seleção.',
            )

        service_request.closed_at = now
        service_request.save(update_fields=["status", "closed_at"])
        log_event(None, "service_request.expired", service_request)
        expired_count += 1
    return expired_count
