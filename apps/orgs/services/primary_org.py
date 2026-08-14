from __future__ import annotations

from typing import Any

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError

from apps.core.models import Setting
from apps.orgs.models import OrgBase

PRIMARY_ORG_SETTING_NAME = "primary_organization"
PRIMARY_ORG_SETTING_PURPOSE = "wc:db_defaults"
PRIMARY_ORG_SETTING_PARENT_MODEL = "customer"


def _pick_gl_code(source: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = source.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _extract_default_gl_accounts(org: OrgBase) -> dict[str, str]:
    raw_accounts = org.gl_accounts if isinstance(org.gl_accounts, dict) else {}
    mapped = {
        "revenue": _pick_gl_code(raw_accounts, "revenue", "sales"),
        "inventory": _pick_gl_code(raw_accounts, "inventory"),
        "cogs": _pick_gl_code(raw_accounts, "cogs", "cost", "expense"),
        "purchase": _pick_gl_code(raw_accounts, "purchase", "payables", "accounts_payable"),
        "variance": _pick_gl_code(raw_accounts, "variance"),
        "commission": _pick_gl_code(raw_accounts, "commission"),
        "tax_payable": _pick_gl_code(raw_accounts, "tax_payable", "tax"),
    }
    return {key: value for key, value in mapped.items() if value}


def _build_primary_org_payload(org: OrgBase) -> dict[str, Any]:
    default_gl_accounts = _extract_default_gl_accounts(org)
    return {
        "org_id": org.pk,
        "org_type": org.org_type,
        "company": org.company,
        "display_name": org.display_name,
        "is_active": org.is_active,
        "default_gl_accounts": default_gl_accounts,
    }


def get_primary_org_setting() -> Setting | None:
    return (
        Setting.objects.filter(
            purpose=PRIMARY_ORG_SETTING_PURPOSE,
            name=PRIMARY_ORG_SETTING_NAME,
            parent_model=PRIMARY_ORG_SETTING_PARENT_MODEL,
            is_active=True,
        )
        .order_by("-dt_modified", "-id")
        .first()
    )


def get_primary_org_id() -> int | None:
    override_id = getattr(settings, "WC_PRIMARY_ORG_ID", None)
    if isinstance(override_id, int) and override_id > 0:
        return override_id

    setting = get_primary_org_setting()
    if not setting:
        return None
    data = setting.config or {}
    org_id = data.get("org_id")
    return org_id if isinstance(org_id, int) and org_id > 0 else None


def get_primary_org() -> OrgBase | None:
    org_id = get_primary_org_id()
    if not org_id:
        return None
    return OrgBase.objects.filter(pk=org_id).first()


def validate_primary_org_candidate(org: OrgBase) -> None:
    if not org.pk:
        raise ValidationError("Primary organization candidate must be saved first.")
    if not org.is_active:
        raise ValidationError("Primary organization must be active.")
    if (org.org_type or "").lower() not in {"customer", "other"}:
        raise ValidationError(
            "Primary organization should normally be an internal customer/organization record. "
            f"Received org_type={org.org_type!r}."
        )


def set_primary_org(org: OrgBase, *, actor=None) -> Setting:
    validate_primary_org_candidate(org)

    if actor is not None:
        if not bool(getattr(actor, "is_superuser", False)):
            raise PermissionDenied("Only superusers may change the primary organization.")

    payload = _build_primary_org_payload(org)

    setting, _created = Setting.objects.get_or_create(
        purpose=PRIMARY_ORG_SETTING_PURPOSE,
        name=PRIMARY_ORG_SETTING_NAME,
        parent_model=PRIMARY_ORG_SETTING_PARENT_MODEL,
        defaults={
            "role": "system",
            "config": payload,
            "is_active": True,
        },
    )

    setting.role = "system"
    setting.is_active = True
    setting.config = payload
    setting.save(update_fields=["role", "is_active", "config", "dt_modified"])
    return setting
