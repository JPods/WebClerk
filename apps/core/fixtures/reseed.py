from __future__ import annotations
from typing import Dict, Iterable, List, Sequence
from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.db import transaction

from apps.core.fixtures import get_seeders

DEFAULT_PASSWORD = "1"

def ensure_superusers(emails: Iterable[str], password: str = DEFAULT_PASSWORD) -> List[int]:
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
            create_kwargs["username"] = (email.split("@")[0] or email)
        user, created = User.objects.get_or_create(**create_kwargs)
        if created or not (user.is_superuser and user.is_staff):
            user.is_staff = True
            user.is_superuser = True
            user.set_password(password)
            user.save()
        ids.append(user.pk)
    return ids

def run_registered_seeders(per_model: int, context: Dict | None = None) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    ctx = context or {}
    for label, seeder in get_seeders().items():
        try:
            ids = seeder(per_model, ctx)
            counts[label] = len(ids or [])
        except Exception:
            counts[label] = 0
    return counts

def seed_default_connections_safe(context: Dict | None = None) -> Dict:
    try:
        from apps.core.fixtures.connections import seed_default_connections
        return seed_default_connections(context or {})
    except Exception:
        return {"created": [], "updated": [], "skipped": [], "error": True}

@transaction.atomic
def seed_all(per_model: int = 5, superuser_emails: Sequence[str] | None = None, with_connections: bool = False) -> Dict:
    summary: Dict = {"superusers": [], "counts": {}, "connections": {}}
    if superuser_emails:
        summary["superusers"] = ensure_superusers(superuser_emails)
    summary["counts"] = run_registered_seeders(per_model, {"superusers": summary["superusers"]})
    if with_connections:
        summary["connections"] = seed_default_connections_safe({"superusers": summary["superusers"]})
    return summary

def reseed_all(
    per_model: int = 5,
    superuser_emails: Sequence[str] | None = ("1@1",),
    with_connections: bool = False,
    reset: bool = False,
    nuke: bool = False,
) -> Dict:
    """
    One-stop reseed:
    - nuke: flush + migrate + seed
    - reset: flush + seed
    - default: seed only
    Returns summary dict with superusers, counts, and connections keys.
    """
    if nuke:
        call_command("flush", "--no-input")
        call_command("migrate")
    elif reset:
        call_command("flush", "--no-input")
    return seed_all(per_model=per_model, superuser_emails=list(superuser_emails or []), with_connections=with_connections)