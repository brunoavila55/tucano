from celery import shared_task

from .backup import run_postgres_backup


@shared_task
def backup_database():
    return run_postgres_backup()
