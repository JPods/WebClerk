"""Purpose lists — each model's own, in its definition (Bill, 2026-10-28).

A model's purposes are config.selectlists.purpose on its wc:model Setting, edited by an
administrator. A record is refused when it is made with, or changed to, a purpose its model
does not list; a value already stored is left alone until it is rewritten. A model whose
definition lists no purposes is not checked, and an empty purpose is always allowed.
"""
from __future__ import annotations

from typing import Optional


def _values(options) -> Optional[frozenset]:
    if not isinstance(options, list):
        return None
    return frozenset(str(o.get('value') if isinstance(o, dict) else o) for o in options
                     if (o.get('value') if isinstance(o, dict) else o))


def allowed_purposes(name: str) -> Optional[frozenset]:
    """The purposes model `name` lists; None when it lists none (not checked)."""
    from apps.core.services import definition
    from apps.core.services.access import model_key
    key = model_key(name) or name
    return definition.part(key, ('selectlists', 'purpose'), _values)


def unlisted(name: str, purpose) -> Optional[str]:
    """Why `purpose` may not be used on model `name`, or None when it may."""
    if not purpose:
        return None
    allowed = allowed_purposes(name)
    if allowed is None or str(purpose) in allowed:
        return None
    return (f"'{purpose}' is not a {name} purpose. Choose one of: {', '.join(sorted(allowed))} "
            f"— or an administrator adds it to the {name} definition (config.selectlists.purpose).")
