from celery import shared_task

from .services import expire_due_requests


@shared_task
def expire_due_service_requests():
    return expire_due_requests()
