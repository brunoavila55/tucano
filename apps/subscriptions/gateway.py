"""Integração com Mercado Pago (stack.md §9) — cobrança da assinatura Premium.

Nunca ativa Premium sem confirmação real do Mercado Pago: sem token
configurado, `create_checkout_preapproval` recusa explicitamente em vez de
liberar o plano de graça. Cancelamento local é sempre seguro (só reduz
acesso, nunca concede), por isso não depende de credenciais.
"""

import logging

from django.conf import settings

from apps.moderation.audit import log_event

from .models import Subscription

logger = logging.getLogger("tucano.subscriptions")


def is_configured():
    return bool(settings.MERCADOPAGO_ACCESS_TOKEN and settings.MERCADOPAGO_PREAPPROVAL_PLAN_ID)


def create_checkout_preapproval(user, back_url):
    if not is_configured():
        raise RuntimeError("Mercado Pago não está configurado neste ambiente.")

    import mercadopago

    sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)
    result = sdk.preapproval().create(
        {
            "preapproval_plan_id": settings.MERCADOPAGO_PREAPPROVAL_PLAN_ID,
            "payer_email": user.email,
            "external_reference": str(user.pk),
            "back_url": back_url,
        }
    )
    response = result["response"]
    subscription = Subscription.for_user(user)
    subscription.mercadopago_preapproval_id = response.get("id", "")
    subscription.status = Subscription.Status.PAST_DUE  # vira ACTIVE só quando o webhook confirmar
    subscription.save(update_fields=["mercadopago_preapproval_id", "status"])
    return response.get("init_point")


def cancel_preapproval(subscription):
    if subscription.mercadopago_preapproval_id and is_configured():
        import mercadopago

        sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)
        try:
            sdk.preapproval().update(subscription.mercadopago_preapproval_id, {"status": "cancelled"})
        except Exception:
            logger.warning("Falha ao cancelar preapproval no Mercado Pago", exc_info=True)

    subscription.plan = Subscription.Plan.FREE
    subscription.status = Subscription.Status.CANCELLED
    subscription.save(update_fields=["plan", "status"])
    log_event(subscription.user, "subscription.cancelled", subscription)
    return subscription


def handle_webhook(payload):
    """Processa a notificação assíncrona do Mercado Pago sobre o preapproval."""
    external_reference = payload.get("external_reference")
    status = payload.get("status")
    preapproval_id = payload.get("id")
    if not external_reference:
        return None

    from django.contrib.auth import get_user_model

    User = get_user_model()
    try:
        user = User.objects.get(pk=external_reference)
    except (User.DoesNotExist, ValueError, TypeError):
        return None

    subscription = Subscription.for_user(user)
    if preapproval_id:
        subscription.mercadopago_preapproval_id = preapproval_id

    if status == "authorized":
        subscription.plan = Subscription.Plan.PREMIUM
        subscription.status = Subscription.Status.ACTIVE
    elif status in ("cancelled", "paused"):
        subscription.plan = Subscription.Plan.FREE
        subscription.status = Subscription.Status.CANCELLED

    subscription.save()
    log_event(None, "subscription.webhook_processed", subscription, status=status)
    return subscription
