from typing import Iterable, List
from django.apps import apps as django_apps
from django.contrib.auth import get_user_model
from django.db import transaction
from apps.core.fixtures import get_seeders, register_seeder

DEFAULT_PASSWORD = "1"

def _ensure_superusers(emails: Iterable[str]) -> List[int]:
    User = get_user_model()
    ids: List[int] = []
    for email in emails:
        email = (email or "").strip().lower()
        if not email:
            continue
        # Prefer email field if present; fall back to username
        create_kwargs = {}
        if "email" in {f.name for f in User._meta.get_fields()}:
            create_kwargs["email"] = email
        if "username" in {f.name for f in User._meta.get_fields()}:
            create_kwargs["username"] = email.split("@")[0] or email
        user, created = User.objects.get_or_create(**create_kwargs)
        if created or not user.is_superuser:
            user.is_staff = True
            user.is_superuser = True
            user.set_password(DEFAULT_PASSWORD)
            user.save()
        ids.append(user.pk)
    return ids

@transaction.atomic
def seed_all(per_model: int = 5, superuser_emails: List[str] | None = None) -> dict:
    """
    Central seeding function.
    - Ensures superusers (e.g., 1@1) exist with password "1".
    - Runs registered model seeders to create 'per_model' records per model with sane relations.
    Returns summary counts by model label.
    """
    summary: dict = {"superusers": []}
    if superuser_emails:
        summary["superusers"] = _ensure_superusers(superuser_emails)

    counts: dict = {}
    for label, fn in get_seeders().items():
        try:
            ids = fn(per_model, {"superusers": summary["superusers"]})
            counts[label] = len(ids)
        except Exception:
            counts[label] = 0
    summary["counts"] = counts
    return summary

@register_seeder("communications.Domain")
def seed_domain(per: int, ctx: dict):
    from apps.communications.models import Domain
    ids = []
    for i in range(per):
        obj, _ = Domain.objects.get_or_create(path=f"https://example{i}.com", defaults={"type": "website", "is_active": True})
        ids.append(obj.pk)
    return ids