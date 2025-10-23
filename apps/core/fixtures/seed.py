from __future__ import annotations
from typing import Dict, Iterable, List, Sequence
from django.apps import apps as django_apps
from django.contrib.auth import get_user_model
from django.db import transaction
from django.core.management import call_command
from apps.core.fixtures import get_seeders
from apps.core.fixtures.seed import seed_all


DEFAULT_SUPERUSER_EMAILS = ("1@1.com", "2@2.com", "3@3.com")
DEFAULT_PASSWORD = "1111pass"

def _ensure_superusers(emails: Iterable[str], *, password: str = DEFAULT_PASSWORD) -> List[int]:
    User = get_user_model()
    ids: List[int] = []
    fields = {f.name for f in User._meta.get_fields()}
    for raw in emails:
        email = (raw or "").strip().lower()
        if not email:
            continue
        create_kwargs = {}
        if "email" in fields:
            create_kwargs["email"] = email
        if "username" in fields:
            create_kwargs.setdefault("username", email.split("@")[0] or email)
        user, created = User.objects.get_or_create(**create_kwargs)
        if created or not (user.is_staff and user.is_superuser):
            user.is_staff = True
            user.is_superuser = True
            user.set_password(password)
            user.save(update_fields=["is_staff", "is_superuser", "password"])
        ids.append(user.pk)
    return ids

def _run_seeders(per_model: int, context: Dict) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for label, fn in get_seeders().items():
        created_ids = fn(per_model, context) or []
        counts[label] = len(created_ids)
    return counts

def _seed_default_connections(context: Dict) -> Dict:
    try:
        from apps.core.fixtures.connections import seed_default_connections
    except Exception as exc:  # pragma: no cover
        return {"created": [], "updated": [], "skipped": [], "error": str(exc)}
    return seed_default_connections(context)

@transaction.atomic
def seed_all(
    *,
    per_model: int = 5,
    superuser_emails: Sequence[str] | None = None,
    password: str = DEFAULT_PASSWORD,
    with_connections: bool = True,
    flush: bool = False,
    migrate: bool = False,
) -> Dict[str, object]:
    """
    Unified reseed entry point. Handles optional flush/migrate prep,
    ensures patterned superusers, runs registered seeders, and
    optionally seeds default connections.
    """
    operations = {"flushed": False, "migrated": False}
    if flush:
        call_command("flush", "--no-input")
        operations["flushed"] = True
    if migrate:
        call_command("migrate")
        operations["migrated"] = True

    with transaction.atomic():
        superusers = _ensure_superusers(superuser_emails or DEFAULT_SUPERUSER_EMAILS, password=password)
        context = {"superusers": superusers}
        seed_counts = _run_seeders(per_model, context)
        connections = _seed_default_connections(context) if with_connections else {}

    return {
        "operations": operations,
        "superusers": superusers,
        "seed_counts": seed_counts,
        "connections": connections,
    }

# seed_all(flush=True, migrate=True)