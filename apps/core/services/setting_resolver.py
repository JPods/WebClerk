"""
Setting resolver — walks the scope hierarchy to find the effective setting.

Precedence (most specific wins):
    user (contact_id) → role → org (org_id) → system

For legacy purposes that have been consolidated into wc:model, the resolver
transparently extracts the correct config section from the wc:model record.

Usage:
    from apps.core.services.setting_resolver import resolve_setting

    layout = resolve_setting(
        purpose="wc:detail_layout",   # or "wc:model" directly
        parent_model="action",
        contact_id=8,
        org_id=1,
        role="admin",
    )
"""

import logging
from typing import Optional

from apps.core.models.setting import Setting

logger = logging.getLogger("core.settings")

# Legacy purposes now stored as sections within wc:model config
_WC_MODEL_SECTIONS = {
    'wc:detail_layout': 'layout',
    'wc:schema_map': 'schema',
    'wc:enrichment_panels': 'enrichment',
    'wc:workbench_fields': 'columns',
    'wc:keywords': 'search',
    'wc:print_layout': 'print',
    'wc:db_defaults': 'defaults',
}


def resolve_setting(
    purpose: str,
    parent_model: str = "",
    contact_id: int = 0,
    org_id: int = 0,
    role: str = "",
) -> Optional[dict]:
    """Find the most specific active Setting and return its config.

    Checks in order (first match wins):
    1. User-specific: scope=user, contact_id=contact_id
    2. Role-specific: scope=role, role=role, org_id=org_id
    3. Org-specific: scope=org, org_id=org_id
    4. System default: scope=system

    Returns the config dict, or None if no matching Setting found.
    """
    base_q = dict(
        purpose=purpose,
        is_active=True,
    )
    if parent_model:
        base_q["parent_model"] = parent_model

    # 1. User-specific
    if contact_id:
        match = Setting.objects.filter(
            **base_q, scope="user", contact_id=contact_id
        ).first()
        if match:
            logger.debug("resolve_setting: user match id=%s for %s/%s", match.id, purpose, parent_model)
            return match.config

    # 2. Role-specific
    if role:
        role_q = {**base_q, "scope": "role", "role": role}
        if org_id:
            role_q["org_id"] = org_id
        match = Setting.objects.filter(**role_q).first()
        if match:
            logger.debug("resolve_setting: role match id=%s for %s/%s", match.id, purpose, parent_model)
            return match.config

    # 3. Org-specific
    if org_id:
        match = Setting.objects.filter(
            **base_q, scope="org", org_id=org_id
        ).first()
        if match:
            logger.debug("resolve_setting: org match id=%s for %s/%s", match.id, purpose, parent_model)
            return match.config

    # 4. System default
    match = Setting.objects.filter(
        **base_q, scope="system"
    ).first()
    if match:
        logger.debug("resolve_setting: system match id=%s for %s/%s", match.id, purpose, parent_model)
        return match.config

    # 5. Legacy fallback — extract section from wc:model record
    section_key = _WC_MODEL_SECTIONS.get(purpose)
    if section_key and parent_model:
        model_setting = Setting.objects.filter(
            purpose="wc:model", parent_model=parent_model,
            is_active=True, scope="system",
        ).first()
        if model_setting and isinstance(model_setting.config, dict):
            section = model_setting.config.get(section_key)
            if section:
                logger.debug("resolve_setting: wc:model fallback for %s/%s -> config.%s",
                             purpose, parent_model, section_key)
                return section

    # 6. Computed fallback — behaviors and field_groups from model metadata
    if purpose == 'wc:field_behaviors' and parent_model:
        return _compute_behaviors(parent_model)

    logger.debug("resolve_setting: no match for %s/%s", purpose, parent_model)
    return None


def _compute_behaviors(parent_model: str) -> Optional[dict]:
    """Compute field behaviors live from Django model metadata.

    Merges any overrides stored in the wc:model Setting's config.behaviors.
    No separate Setting record needed — the model IS the source of truth.
    """
    from apps.core.services.field_behaviors import (
        get_field_behaviors, get_field_groups, get_leaf_declarations,
        get_model_field_map,
    )
    field_map = get_model_field_map(parent_model)
    if not field_map:
        return None

    # Load overrides from wc:model Setting if it exists
    overrides = None
    model_setting = Setting.objects.filter(
        purpose="wc:model", parent_model=parent_model,
        is_active=True, scope="system",
    ).first()
    if model_setting and isinstance(model_setting.config, dict):
        overrides = model_setting.config.get('behaviors')

    return {
        'behaviors': get_field_behaviors(parent_model, field_map, overrides=overrides),
        'field_groups': get_field_groups(parent_model, list(field_map.keys())),
        'leaves': get_leaf_declarations(parent_model, field_map),
    }


def resolve_setting_with_source(
    purpose: str,
    parent_model: str = "",
    contact_id: int = 0,
    org_id: int = 0,
    role: str = "",
) -> tuple[Optional[dict], str]:
    """Same as resolve_setting but also returns the scope that matched.

    Returns: (config, scope) where scope is 'user', 'role', 'org', 'system', or '' if not found.
    """
    base_q = dict(purpose=purpose, is_active=True)
    if parent_model:
        base_q["parent_model"] = parent_model

    if contact_id:
        match = Setting.objects.filter(**base_q, scope="user", contact_id=contact_id).first()
        if match:
            return match.config, "user"

    if role:
        role_q = {**base_q, "scope": "role", "role": role}
        if org_id:
            role_q["org_id"] = org_id
        match = Setting.objects.filter(**role_q).first()
        if match:
            return match.config, "role"

    if org_id:
        match = Setting.objects.filter(**base_q, scope="org", org_id=org_id).first()
        if match:
            return match.config, "org"

    match = Setting.objects.filter(**base_q, scope="system").first()
    if match:
        return match.config, "system"

    # Legacy fallback — extract section from wc:model record
    section_key = _WC_MODEL_SECTIONS.get(purpose)
    if section_key and parent_model:
        model_setting = Setting.objects.filter(
            purpose="wc:model", parent_model=parent_model,
            is_active=True, scope="system",
        ).first()
        if model_setting and isinstance(model_setting.config, dict):
            section = model_setting.config.get(section_key)
            if section:
                return section, "system"

    # Computed fallback — behaviors from model metadata
    if purpose == 'wc:field_behaviors' and parent_model:
        result = _compute_behaviors(parent_model)
        if result:
            return result, "computed"

    return None, ""
