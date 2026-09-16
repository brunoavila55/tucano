from celery import shared_task
from django.contrib.auth import get_user_model


@shared_task
def notify_user_task(user_id, channel, event_type, title, body):
    from . import notifications

    User = get_user_model()
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return

    if channel == "email":
        notifications.send_email_notification(user, title, body, event_type)
    elif channel == "push":
        notifications.send_push_notification(user, title, body, event_type)
    elif channel == "whatsapp":
        notifications.send_whatsapp_notification(user, body, event_type)
