from __future__ import annotations
from typing import Dict, Iterable, List, Sequence, Tuple
from decimal import Decimal
import uuid
from django.apps import apps as django_apps
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import models
from django.utils import timezone
from apps.core.fixtures import get_seeders, register_seeder

DEFAULT_SUPERUSER_EMAILS = ("1@1.com", "2@2.com", "3@3.com")
DEFAULT_PASSWORD = "1111pass"

# Built-in and infra apps to skip for generic model seeding
_EXCLUDE_APPS = {
    "admin",
    "auth",          # handled by _ensure_superusers
    "contenttypes",
    "sessions",
    "messages",
    "staticfiles",
}

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

def _run_registered_seeders(per_model: int, context: Dict) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for label, fn in get_seeders().items():
        try:
            created_ids = fn(per_model, context) or []
            counts[label] = len(created_ids)
        except Exception:
            counts[label] = counts.get(label, 0)
    return counts

def _model_label(m: type[models.Model]) -> str:
    return f"{m._meta.app_label}.{m._meta.object_name}"

def _is_generic_seed_candidate(m: type[models.Model]) -> bool:
    meta = m._meta
    if meta.abstract or meta.proxy or not meta.managed:
        return False
    if meta.app_label in _EXCLUDE_APPS:
        return False
    return True

def _build_field_value(field: models.Field, idx: int) -> object:
    if isinstance(field, (models.CharField, models.TextField)):
        max_len = getattr(field, "max_length", None)
        base = f"{field.model.__name__} {field.name} {idx}"
        return base[:max_len] if max_len else base
    if isinstance(field, models.SlugField):
        return f"{field.model._meta.model_name}-{idx}"
    if isinstance(field, models.EmailField):
        return f"{field.model._meta.model_name}{idx}@example.com"
    if isinstance(field, models.URLField):
        return f"https://example.com/{field.model._meta.model_name}/{idx}"
    if isinstance(field, (models.IntegerField, models.BigIntegerField, models.SmallIntegerField,
                          models.PositiveIntegerField, models.PositiveSmallIntegerField)):
        return idx
    if isinstance(field, models.BooleanField):
        return bool(idx % 2)
    if isinstance(field, models.FloatField):
        return float(idx or 1)
    if isinstance(field, models.DecimalField):
        return Decimal(idx or 1)
    if isinstance(field, models.DateTimeField):
        return timezone.now()
    if isinstance(field, models.DateField):
        return timezone.now().date()
    if isinstance(field, models.UUIDField):
        return uuid.uuid4()
    if isinstance(field, models.JSONField):
        return {}
    return None

def _generic_create_kwargs(model: type[models.Model], idx: int) -> Tuple[Dict[str, object], List[models.ManyToManyField]]:
    kwargs: Dict[str, object] = {}
    m2m_fields: List[models.ManyToManyField] = []
    for field in model._meta.get_fields():
        if getattr(field, "auto_created", False) and not getattr(field, "concrete", True):
            continue
        if getattr(field, "primary_key", False) and getattr(field, "auto_created", False):
            continue
        if isinstance(field, models.ManyToManyField):
            m2m_fields.append(field)
            continue
        if isinstance(field, (models.ForeignKey, models.OneToOneField)):
            if getattr(field, "null", False):
                kwargs[field.name] = None
            continue
        if hasattr(field, "editable") and field.editable is False:
            continue
        # Some objects returned by get_fields() (e.g. ForeignObjectRel) are not actual
        # Field instances and may not implement has_default(); guard before calling.
        has_default = False
        func = getattr(field, "has_default", None)
        if callable(func):
            try:
                has_default = func()
            except Exception:
                has_default = False
        # Fallback: check if a default value is provided on the attribute itself.
        if not has_default:
            has_default = getattr(field, "default", models.fields.NOT_PROVIDED) is not models.fields.NOT_PROVIDED
        if getattr(field, "null", False) is False or has_default:
            # Narrow the type to actual Field instances before calling _build_field_value
            if isinstance(field, models.Field):
                val = _build_field_value(field, idx)
                if val is not None:
                    kwargs[field.name] = val
    return kwargs, m2m_fields

def _seed_model_generic(model: type[models.Model], per: int) -> int:
    created = 0
    existing = model.objects.count()
    to_make = max(per - existing, 0)
    for i in range(1, to_make + 1):
        try:
            kwargs, m2m_fields = _generic_create_kwargs(model, i)
            obj = model.objects.create(**kwargs)
            for m2m_field in m2m_fields:
                rel_qs = m2m_field.remote_field.model.objects.all()[:1]
                if rel_qs.exists():
                    getattr(obj, m2m_field.name).add(*rel_qs)
            created += 1
        except Exception:
            continue
    return created

def _auto_seed_remaining_models(per_model: int, context: Dict) -> Dict[str, int]:
    registered = set(get_seeders().keys())
    counts: Dict[str, int] = {}
    for model in django_apps.get_models():
        if not _is_generic_seed_candidate(model):
            continue
        label = _model_label(model)
        if label in registered:
            continue
        try:
            num = _seed_model_generic(model, per_model)
            if num:
                counts[label] = num
        except Exception:
            continue
    return counts

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
    Unified reseed entry point: optional flush/migrate, ensure superusers,
    run registered seeders, auto-seed remaining models, and optionally default connections.
    """
    operations = {"flushed": False, "migrated": False}
    if flush:
        call_command("flush", "--no-input")
        operations["flushed"] = True
    if migrate:
        call_command("migrate")
        operations["migrated"] = True

    superusers = _ensure_superusers(superuser_emails or DEFAULT_SUPERUSER_EMAILS, password=password)
    context: Dict[str, object] = {"superusers": superusers}

    reg_counts = _run_registered_seeders(per_model, context)
    auto_counts = _auto_seed_remaining_models(per_model, context)

    connections: Dict = {}
    if with_connections:
        try:
            from apps.core.fixtures.connections import seed_default_connections  # optional
            connections = seed_default_connections(context)
        except Exception:
            connections = {"created": [], "updated": [], "skipped": []}

    return {
        "operations": operations,
        "superusers": superusers,
        "seed_counts": {**reg_counts, **auto_counts},
        "connections": connections,
    }

# Example explicit seeder so you see immediate data in products.Item
@register_seeder("products.Item")
def seed_products_item(per: int, ctx: dict) -> List[int]:
    from apps.products.models import Item
    ids: List[int] = []
    kind_value = getattr(Item, "KIND_PHYSICAL", None) or getattr(Item, "KIND_DEFAULT", None) or 1
    existing = Item.objects.count()
    to_make = max(per - existing, 0)
    for i in range(1, to_make + 1):
        obj, _ = Item.objects.get_or_create(
            name=f"SeedItem {existing + i}",
            defaults={"kind": kind_value},
        )
        ids.append(obj.pk)
    return ids