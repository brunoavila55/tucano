import json
import logging

from django.conf import settings
from django.core.mail import send_mail

from .models import NotificationLog, NotificationPreference

logger = logging.getLogger("tucano.notifications")


def _log(user, channel, event_type, status, detail=""):
    NotificationLog.objects.create(
        user=user, channel=channel, event_type=event_type, status=status, detail=detail
    )


def send_email_notification(user, subject, body, event_type):
    preference = NotificationPreference.for_user(user)
    if not preference.email_enabled or not user.email:
        _log(user, NotificationLog.Channel.EMAIL, event_type, NotificationLog.Status.SKIPPED)
        return
    send_mail(subject, body, None, [user.email], fail_silently=True)
    _log(user, NotificationLog.Channel.EMAIL, event_type, NotificationLog.Status.SENT)


def send_push_notification(user, title, body, event_type):
    preference = NotificationPreference.for_user(user)
    if not preference.push_enabled:
        _log(user, NotificationLog.Channel.PUSH, event_type, NotificationLog.Status.SKIPPED)
        return

    subscriptions = list(user.push_subscriptions.all())
    if not subscriptions:
        _log(user, NotificationLog.Channel.PUSH, event_type, NotificationLog.Status.SKIPPED, "sem inscrição push")
        return

    if not (settings.WEBPUSH_VAPID_PRIVATE_KEY and settings.WEBPUSH_VAPID_PUBLIC_KEY):
        logger.info("Web Push não configurado (sem VAPID) — não enviado: %s", event_type)
        _log(user, NotificationLog.Channel.PUSH, event_type, NotificationLog.Status.SKIPPED, "VAPID não configurado")
        return

    from pywebpush import WebPushException, webpush

    for subscription in subscriptions:
        try:
            webpush(
                subscription_info={
                    "endpoint": subscription.endpoint,
                    "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth},
                },
                data=json.dumps({"title": title, "body": body}),
                vapid_private_key=settings.WEBPUSH_VAPID_PRIVATE_KEY,
                vapid_claims={"sub": settings.WEBPUSH_VAPID_ADMIN_EMAIL},
            )
            _log(user, NotificationLog.Channel.PUSH, event_type, NotificationLog.Status.SENT)
        except WebPushException:
            logger.warning("Falha ao enviar push para user_id=%s", user.pk, exc_info=True)
            _log(user, NotificationLog.Channel.PUSH, event_type, NotificationLog.Status.FAILED)


def send_whatsapp_notification(user, body, event_type):
    preference = NotificationPreference.for_user(user)
    if not preference.whatsapp_enabled or not user.phone_number:
        _log(user, NotificationLog.Channel.WHATSAPP, event_type, NotificationLog.Status.SKIPPED)
        return

    if not (settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN):
        logger.info("WhatsApp/SMS não configurado (sem credenciais) — não enviado: %s", event_type)
        _log(user, NotificationLog.Channel.WHATSAPP, event_type, NotificationLog.Status.SKIPPED, "Twilio não configurado")
        return

    from twilio.rest import Client

    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    try:
        client.messages.create(
            from_=f"whatsapp:{settings.TWILIO_WHATSAPP_FROM}",
            to=f"whatsapp:{user.phone_number}",
            body=body,
        )
        _log(user, NotificationLog.Channel.WHATSAPP, event_type, NotificationLog.Status.SENT)
    except Exception:
        logger.warning("Falha ao enviar WhatsApp para user_id=%s", user.pk, exc_info=True)
        _log(user, NotificationLog.Channel.WHATSAPP, event_type, NotificationLog.Status.FAILED)


def dispatch_notification(user, event_type, title, body, urgent=False):
    """Decide os canais e enfileira o envio (AGENTS.md — Notificações em camadas)."""
    from . import tasks

    preference = NotificationPreference.for_user(user)
    if preference.push_enabled:
        tasks.notify_user_task.delay(user.pk, "push", event_type, title, body)
    if urgent and preference.whatsapp_enabled:
        tasks.notify_user_task.delay(user.pk, "whatsapp", event_type, title, body)
    if preference.email_enabled:
        tasks.notify_user_task.delay(user.pk, "email", event_type, title, body)
