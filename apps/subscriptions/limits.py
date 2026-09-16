from datetime import timedelta

from django.utils import timezone

from .models import Subscription

FREE_MONTHLY_REQUEST_LIMIT = 5


def can_client_publish_request(client_user):
    """Modelo freemium (AGENTS.md): contratante gratuito tem chamados limitados."""
    subscription = Subscription.for_user(client_user)
    if subscription.is_premium:
        return True, None

    from apps.requests.models import ServiceRequest

    count = (
        ServiceRequest.objects.filter(
            client__user=client_user,
            published_at__gte=timezone.now() - timedelta(days=30),
        )
        .exclude(status=ServiceRequest.Status.DRAFT)
        .count()
    )
    if count >= FREE_MONTHLY_REQUEST_LIMIT:
        return False, (
            f"Plano gratuito permite até {FREE_MONTHLY_REQUEST_LIMIT} chamados a cada 30 dias. "
            "Assine o Premium para publicar sem limite."
        )
    return True, None
