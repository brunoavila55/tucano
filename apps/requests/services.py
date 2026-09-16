from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.chat.models import Conversation
from apps.moderation.audit import log_event

from .models import Interest, ServiceRequest


def _finalize_remaining_interests(service_request, final_status):
    service_request.interests.filter(status=Interest.Status.APPLIED).update(status=final_status)


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
        _finalize_remaining_interests(service_request, Interest.Status.NOT_SELECTED)
        service_request.save(update_fields=["status", "closed_at"])
    else:
        service_request.status = ServiceRequest.Status.PARTIALLY_FILLED
        service_request.save(update_fields=["status"])

    Conversation.objects.get_or_create(interest=interest)
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
        _finalize_remaining_interests(service_request, Interest.Status.NOT_SELECTED)
    elif selected_count > 0:
        service_request.status = ServiceRequest.Status.PARTIALLY_FILLED
        _finalize_remaining_interests(service_request, Interest.Status.NOT_SELECTED)
    else:
        service_request.status = ServiceRequest.Status.EXPIRED
        _finalize_remaining_interests(service_request, Interest.Status.EXPIRED)

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
    _finalize_remaining_interests(service_request, Interest.Status.EXPIRED)
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
            _finalize_remaining_interests(service_request, Interest.Status.NOT_SELECTED)
        elif selected_count > 0:
            service_request.status = ServiceRequest.Status.PARTIALLY_FILLED
            _finalize_remaining_interests(service_request, Interest.Status.NOT_SELECTED)
        else:
            service_request.status = ServiceRequest.Status.EXPIRED
            _finalize_remaining_interests(service_request, Interest.Status.EXPIRED)

        service_request.closed_at = now
        service_request.save(update_fields=["status", "closed_at"])
        log_event(None, "service_request.expired", service_request)
        expired_count += 1
    return expired_count
