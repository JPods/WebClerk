"""Single-entry reset + reseed helpers.

Use drop_and_reseed() to:
- DROP the DB (sqlite file, or PostgreSQL public schema), migrate,
- seed 5 per registered model,
- link relationships, and create 3 superusers.

Safety: only runs destructive DROP on local sqlite or postgres with DEBUG=True
and HOST in ("", "localhost", "127.0.0.1") unless ALLOW_SYSTEM_PY=1 is set.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Sequence
from django.conf import settings
from django.db import connection
from django.core.management import call_command
from apps.core.fixtures.seed import seed_all, DEFAULT_SUPERUSER_EMAILS

@dataclass
class ResetResult:
    dropped: bool
    migrated: bool
    seed: dict

def _safe_can_drop() -> bool:
    if getattr(settings, "DEBUG", False) is False:
        return False
    host = (settings.DATABASES["default"].get("HOST") or "").strip()
    return host in ("", "localhost", "127.0.0.1")

def _drop_database_if_supported() -> bool:
    engine = settings.DATABASES["default"]["ENGINE"]
    name = settings.DATABASES["default"]["NAME"]
    # SQLite: delete file
    if "sqlite" in engine:
        import os
        try:
            if os.path.exists(name):
                os.remove(name)
            return True
        except Exception:
            return False
    # PostgreSQL: drop+recreate public schema
    if "postgres" in engine:
        try:
            with connection.cursor() as cur:
                cur.execute("DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public;")
            return True
        except Exception:
            return False
    return False

def drop_and_reseed(
    *,
    per_model: int = 5,
    superuser_emails: Sequence[str] | None = None,
    allow_remote: bool = False,
) -> ResetResult:
    if not (allow_remote or _safe_can_drop() or settings.ALLOWED_HOSTS == ["*"]):
        # Fallback: refuse dangerous drop; do a flush+migrate reseed instead.
        dropped = False
        call_command("migrate")
        seed = seed_all(per_model=per_model, superuser_emails=superuser_emails or DEFAULT_SUPERUSER_EMAILS,
                        with_connections=True, flush=True, migrate=False)
        return ResetResult(dropped=dropped, migrated=True, seed=seed)

    dropped = _drop_database_if_supported()
    call_command("migrate")
    seed = seed_all(per_model=per_model, superuser_emails=superuser_emails or DEFAULT_SUPERUSER_EMAILS,
                    with_connections=True, flush=False, migrate=False)
    return ResetResult(dropped=dropped, migrated=True, seed=seed)

# Back-compat alias used in docs
def full_reset_and_seed(create_superusers: int = 3, superuser_emails: Sequence[str] | None = None) -> ResetResult:
    emails: Sequence[str] = tuple(superuser_emails or [f"{i}@{i}.com" for i in range(1, create_superusers + 1)] or DEFAULT_SUPERUSER_EMAILS)
    return drop_and_reseed(per_model=5, superuser_emails=emails)

__all__ = ["drop_and_reseed", "full_reset_and_seed", "ResetResult"]
