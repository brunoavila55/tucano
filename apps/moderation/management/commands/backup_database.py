from django.core.management.base import BaseCommand

from apps.moderation.backup import run_postgres_backup


class Command(BaseCommand):
    help = "Roda um backup do Postgres agora (pg_dump comprimido) e aplica retenção."

    def handle(self, *args, **options):
        path = run_postgres_backup()
        self.stdout.write(self.style.SUCCESS(f"Backup criado em {path}"))
