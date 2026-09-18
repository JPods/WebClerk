from __future__ import annotations
"""Date/time field & JSON key normalization helpers.

Goals:
  * Enforce project convention that timestamp / datetime fields & JSON keys
    are prefixed with `dt_` and stored in UTC.
  * Provide scanning utilities used by the management command
    `check_dt_conventions` to report non‑conforming fields and suggest
    rename targets.

Rules Implemented:
  1. Model field names representing instants must start with `dt_`.
     Accepted Django field types: DateTimeField, DateField, BigIntegerField,
     IntegerField (when heuristically timestamp-like), and Positive(Big)Integer.
    2. Existing legacy pattern `dt_<name>` must migrate to `dt_<name>`.
         Example legacy: dt_created / dt_modified  →  canonical: dt_created / dt_modified.
  3. Millisecond epoch integer fields are allowed; they still must be `dt_*`.
  4. JSON keys beginning with `dt_` should either be:
       * ISO8601 UTC ending with 'Z' (YYYY-MM-DDTHH:MM:SS[.fff]Z), OR
       * Integer epoch milliseconds.

This module avoids importing Django models at import time beyond lightweight
introspection so it is safe to import inside a management command.
"""
from dataclasses import dataclass
from typing import Iterable, List, Dict, Any, cast
from django.apps import apps as django_apps
from django.db import models
import re

TIMESTAMP_FIELD_TYPES = {
    'DateTimeField', 'DateField', 'BigIntegerField', 'IntegerField',
    'PositiveIntegerField', 'PositiveBigIntegerField'
}

LEGACY_SUFFIX = '_dt'

ISO_Z_RE = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,6})?Z$')

@dataclass
class DtFieldViolation:
    app_label: str
    model: str
    field: str
    field_type: str
    reason: str
    suggested: str | None = None

    def as_dict(self) -> Dict[str, Any]:
        return {
            'app': self.app_label,
            'model': self.model,
            'field': self.field,
            'type': self.field_type,
            'reason': self.reason,
            'suggested': self.suggested,
        }


def is_timestamp_candidate(field: models.Field) -> bool:
    ft = field.get_internal_type()
    if ft in TIMESTAMP_FIELD_TYPES:
        return True
    return False


def suggest_new_name(name: str) -> str | None:
    if name.startswith('dt_'):
        return None
    if name.endswith(LEGACY_SUFFIX):
        base = name[:-3]  # strip _dt
        return f'dt_{base}'
    # created, modified special cases
    if name in {'created', 'modified'}:
        return f'dt_{name}'
    # common variations
    if name.endswith('_time'):
        return 'dt_' + name[:-5]
    if name.endswith('_date'):
        return 'dt_' + name[:-5]
    return None


def scan_model_fields() -> List[DtFieldViolation]:
    violations: List[DtFieldViolation] = []
    for model in django_apps.get_models():
        opts = model._meta
        for field in opts.get_fields():
            if not isinstance(field, models.Field):
                continue
            if field.auto_created:
                continue
            if not is_timestamp_candidate(field):
                continue
            name = field.name
            if name.startswith('dt_'):
                continue
            suggested = suggest_new_name(name)
            if suggested is None:
                reason = 'timestamp-like field not prefixed dt_'
            else:
                reason = 'legacy suffix _dt should be migrated to dt_<name>' if name.endswith(LEGACY_SUFFIX) else 'rename to dt_ prefix'
            violations.append(
                DtFieldViolation(
                    app_label=opts.app_label,
                    model=cast(str, opts.object_name),
                    field=name,
                    field_type=field.get_internal_type(),
                    reason=reason,
                    suggested=suggested,
                )
            )
    return violations


def normalize_json_dt_value(value: Any):
    """Return a normalized representation or original if not convertible.

    * If int-like string, convert to int.
    * If ISO with timezone offset '+00:00', convert to trailing 'Z'.
    Function intentionally lightweight; not recursive.
    """
    if value is None:
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        if value.isdigit():
            try:
                return int(value)
            except Exception:  # pragma: no cover
                return value
        # Convert trailing +00:00 to Z
        if value.endswith('+00:00'):
            core = value[:-6]
            # ensure T present
            if 'T' in core:
                return core + 'Z'
        # Accept already normalized
        if ISO_Z_RE.match(value):
            return value
    return value


def normalize_json_dt_payload(obj: Any):
    """Recursively normalize any keys starting with dt_."""
    if isinstance(obj, dict):
        for k, v in list(obj.items()):
            if k.startswith('dt_'):
                obj[k] = normalize_json_dt_value(v)
            else:
                obj[k] = normalize_json_dt_payload(v)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            obj[i] = normalize_json_dt_payload(v)
    return obj

__all__ = [
    'scan_model_fields', 'DtFieldViolation', 'normalize_json_dt_payload', 'normalize_json_dt_value'
]
