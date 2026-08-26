"""
Dot-path utilities for nested dicts and Django model objects.

Single source of truth — all dot-path resolution goes through here.

Three functions:
  get_nested_value(obj, path)   — read
  set_nested_value(obj, path, v) — write (creates intermediate dicts)
  delete_nested_value(obj, path) — remove key or set attr to None

All handle both plain dicts and objects with attributes (Django models).
"""
from __future__ import annotations

from typing import Any


def get_nested_value(obj: Any, path: str, *, default: Any = None) -> Any:
    """Get a nested value using dot notation.

    Works on dicts, Django model instances, or any mix.
    For FK fields that are callable (related managers), calls them.

    Args:
        obj:     Source object or dict.
        path:    Dotted path like ``"totals.total"`` or ``"customer.name"``.
        default: Returned when any segment is missing (default ``None``).

    Returns:
        The resolved value, or *default* if the path cannot be followed.
    """
    if obj is None or not path:
        return default

    parts = path.split(".")
    current = obj

    for part in parts:
        if current is None:
            return default
        if isinstance(current, dict):
            if part in current:
                current = current[part]
            else:
                return default
        elif hasattr(current, part):
            val = getattr(current, part)
            # FK / related-manager: call if callable and not a plain string
            if callable(val) and not isinstance(val, str):
                try:
                    current = val()
                except Exception:
                    return default
            else:
                current = val
        else:
            return default

    return current


def set_nested_value(obj: Any, path: str, value: Any) -> bool:
    """Set a nested value using dot notation.

    Creates intermediate dicts as needed.  Returns ``True`` on success.
    """
    if not path:
        return False

    parts = path.split(".")
    current = obj

    for part in parts[:-1]:
        if hasattr(current, part):
            next_obj = getattr(current, part)
            if not isinstance(next_obj, (dict, list)):
                setattr(current, part, {})
                next_obj = getattr(current, part)
            current = next_obj
        elif isinstance(current, dict):
            if part not in current or not isinstance(current[part], dict):
                current[part] = {}
            current = current[part]
        else:
            return False

    last = parts[-1]
    if hasattr(current, last):
        setattr(current, last, value)
    elif isinstance(current, dict):
        current[last] = value
    else:
        return False
    return True


def delete_nested_value(obj: Any, path: str) -> bool:
    """Delete a nested value using dot notation.

    For dicts: removes the key.  For objects: sets the attribute to ``None``.
    Returns ``True`` on success.
    """
    if not path:
        return False

    parts = path.split(".")
    current = obj

    for part in parts[:-1]:
        if current is None:
            return False
        if isinstance(current, dict) and part in current:
            current = current[part]
        elif hasattr(current, part):
            current = getattr(current, part)
        else:
            return False

    last = parts[-1]
    if isinstance(current, dict) and last in current:
        del current[last]
    elif hasattr(current, last):
        setattr(current, last, None)
    else:
        return False
    return True
