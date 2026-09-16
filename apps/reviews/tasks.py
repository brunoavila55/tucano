from celery import shared_task

from .services import create_pending_confirmations


@shared_task
def ask_pending_confirmations():
    return create_pending_confirmations()
