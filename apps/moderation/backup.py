"""Backup automatizado do Postgres (AGENTS.md — dado sensível exige isso
desde o primeiro dia). Nunca loga a senha: ela só é passada via PGPASSWORD
no ambiente do subprocesso, nunca como argumento de linha de comando nem
em mensagem de log.
"""

import gzip
import logging
import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

from django.conf import settings

logger = logging.getLogger("tucano.backup")

BACKUP_DIR = Path(settings.BASE_DIR) / "backups"
RETENTION_DAYS = 14


def run_postgres_backup():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    db = settings.DATABASES["default"]

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = BACKUP_DIR / f"tucano-{timestamp}.sql.gz"

    env = os.environ.copy()
    if db.get("PASSWORD"):
        env["PGPASSWORD"] = db["PASSWORD"]

    dump_cmd = [
        "pg_dump",
        "-h", db.get("HOST") or "db",
        "-p", str(db.get("PORT") or 5432),
        "-U", db.get("USER") or "postgres",
        db.get("NAME"),
    ]
    result = subprocess.run(dump_cmd, env=env, stdout=subprocess.PIPE, check=True)
    dest.write_bytes(gzip.compress(result.stdout))

    removed = _apply_retention()
    logger.info("Backup criado: %s (removidos %d backups antigos)", dest.name, removed)
    return str(dest)


def _apply_retention():
    cutoff = datetime.now(timezone.utc).timestamp() - RETENTION_DAYS * 86400
    removed = 0
    for path in BACKUP_DIR.glob("tucano-*.sql.gz"):
        if path.stat().st_mtime < cutoff:
            path.unlink()
            removed += 1
    return removed
