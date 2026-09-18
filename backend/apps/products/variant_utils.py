from __future__ import annotations

import uuid
from typing import Dict, Iterable, Tuple


def _normalize_pair(k: str, v) -> Tuple[str, str]:
    k_norm = str(k).strip().lower()
    v_norm = str(v).strip().lower()
    return k_norm, v_norm


def canonicalize_variant_key(attrs: Dict[str, object]) -> str:
    """Return a stable canonical key string from attribute dict.

    Example: {"Color": "Blue", "size": "M"} -> "color=blue|size=m"
    Keys sorted A->Z, trimmed, lowercased; values stringified, trimmed, lowercased.
    """
    if not isinstance(attrs, dict):
        return ""
    pairs = [_normalize_pair(k, attrs[k]) for k in attrs.keys()]
    pairs.sort(key=lambda t: t[0])
    return "|".join(f"{k}={v}" for k, v in pairs)


def derive_variant_set_uuid(parent_uuid: uuid.UUID | str) -> uuid.UUID:
    """Deterministically derive a variant family UUID from parent item UUID.

    Uses UUIDv5 with URL namespace and a clear salt prefix.
    """
    pu = uuid.UUID(str(parent_uuid))
    return uuid.uuid5(uuid.NAMESPACE_URL, f"variant-set:{pu}")


def derive_variant_uuid(set_uuid: uuid.UUID | str, attrs: Dict[str, object]) -> uuid.UUID:
    """Derive deterministic variant UUID from set_uuid and canonicalized attrs.

    The same attribute combination always maps to the same UUID within the set.
    """
    su = uuid.UUID(str(set_uuid))
    name = canonicalize_variant_key(attrs)
    return uuid.uuid5(su, name)


def validate_variant_attrs(attrs: Dict[str, object], schema: Dict[str, Iterable[object]] | None) -> tuple[bool, list[str]]:
    """Light validation of attribute keys/values against optional schema.

    Schema shape: {key: iterable_of_allowed_values}. If schema is None, always pass.
    Returns (ok, errors).
    """
    errors: list[str] = []
    if not schema:
        return True, errors
    if not isinstance(attrs, dict):
        return False, ["attrs must be dict"]
    # Normalize schema allowed sets
    allowed = {str(k).strip().lower(): {str(v).strip().lower() for v in vals} for k, vals in schema.items()}
    for k, v in attrs.items():
        kn, vn = _normalize_pair(k, v)
        if kn not in allowed:
            errors.append(f"unknown attribute '{kn}'")
            continue
        if allowed[kn] and vn not in allowed[kn]:
            errors.append(f"invalid value '{vn}' for '{kn}'")
    return (len(errors) == 0), errors
