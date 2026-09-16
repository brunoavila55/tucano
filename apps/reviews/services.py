from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.accounts.notifications import dispatch_notification
from apps.moderation.audit import log_event

from .models import Review, ServiceConfirmation


def get_or_create_confirmation(interest):
    confirmation, _ = ServiceConfirmation.objects.get_or_create(interest=interest)
    return confirmation


def create_pending_confirmations():
    """Varredura periódica (Celery beat): pergunta às duas partes se o serviço ocorreu."""
    from apps.requests.models import Interest

    due_interests = Interest.objects.filter(
        status=Interest.Status.SELECTED,
        service_request__scheduled_start__lte=timezone.now(),
        confirmation__isnull=True,
    ).select_related("service_request__client__user", "professional__user")

    created = 0
    for interest in due_interests:
        confirmation = ServiceConfirmation.objects.create(interest=interest)
        title = f'O serviço "{interest.service_request.title}" aconteceu?'
        body = "Confirme para liberar a avaliação bilateral."
        dispatch_notification(interest.service_request.client.user, "service_confirmation.requested", title, body)
        dispatch_notification(interest.professional.user, "service_confirmation.requested", title, body)
        created += 1
    return created


def confirm_service(confirmation, user, occurred):
    interest = confirmation.interest
    is_client = user == interest.service_request.client.user
    is_professional = user == interest.professional.user
    if not (is_client or is_professional):
        raise ValidationError("Você não participa desta interação.")

    now = timezone.now()
    if is_client:
        confirmation.client_confirmed = occurred
        confirmation.client_responded_at = now
        confirmation.save(update_fields=["client_confirmed", "client_responded_at"])
    else:
        confirmation.professional_confirmed = occurred
        confirmation.professional_responded_at = now
        confirmation.save(update_fields=["professional_confirmed", "professional_responded_at"])

    if confirmation.has_dispute:
        log_event(user, "service_confirmation.disputed", confirmation)
    else:
        log_event(user, "service_confirmation.answered", confirmation, occurred=occurred)
    return confirmation


def submit_review(confirmation, author, target, rating, comment):
    if not confirmation.is_legitimate:
        raise ValidationError(
            "Avaliação só é permitida depois que as duas partes confirmam que o serviço ocorreu."
        )
    if Review.objects.filter(confirmation=confirmation, author=author).exists():
        raise ValidationError("Você já avaliou esta interação.")

    review = Review.objects.create(
        confirmation=confirmation, author=author, target=target, rating=rating, comment=comment
    )
    log_event(author, "review.submitted", review)
    return review


def contest_review(review, contester, reason):
    if contester != review.target:
        raise ValidationError("Só quem foi avaliado pode contestar a avaliação.")
    if review.contested:
        raise ValidationError("Esta avaliação já foi contestada.")

    review.contested = True
    review.contest_reason = reason
    review.save(update_fields=["contested", "contest_reason"])
    log_event(contester, "review.contested", review, reason=reason)
    return review
