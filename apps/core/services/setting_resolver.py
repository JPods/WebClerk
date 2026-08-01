"""
Setting resolver — walks the scope hierarchy to find the effective setting.

Precedence (most specific wins):
    user (contact_id) → role → org (org_id) → system

Usage:
    from apps.core.services.setting_resolver import resolve_setting

    # Get the detail layout for action, for this user
    layout = resolve_setting(
        purpose="detail_layout",
        parent_model="action",
        contact_id=8,
        org_id=1,
        role="admin",
    )

    # Returns the config from the most specific matching Setting,
    # or None if no Setting exists at any level.
"""

import logging
from typing import Optional, Any

from apps.core.models.setting import Setting

logger = logging.getLogger("core.settings")


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

    logger.debug("resolve_setting: no match for %s/%s", purpose, parent_model)
    return None


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

    return None, ""
