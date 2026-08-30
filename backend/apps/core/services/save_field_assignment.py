"""Field assignment service for the universal save pipeline.

Extracted from save_view.py — handles field coercion, JSON deep merge,
FK normalization, mode dispatch (update/insert/delete), and unknown field
routing to prefs.userdefined.

Part of the save_* service cluster:
  save_field_assignment.py  — this file
  save_line_processing.py   — line CRUD for header models
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from django.db import models

from apps.core.services.field_behaviors import _I18N_FIELDS as _i18n_field_set
from common.json_path import delete_nested_value

console_logger = logging.getLogger('console')

MAX_FIELD_SIZE = 15000
UNKNOWN_FIELD_MAX_CHARS = 256

SKIP_FIELDS = frozenset({
    'model_name', 'id', 'version', 'expected_version',
    'bulk', 'lines', 'uuid', 'record', 'options',
})

INT_FIELD_TYPES = (
    models.AutoField,
    models.IntegerField,
    models.BigIntegerField,
    models.SmallIntegerField,
    models.PositiveIntegerField,
    models.PositiveSmallIntegerField,
)

NUMERIC_FIELD_NAMES = frozenset({
    'DecimalField', 'FloatField', 'IntegerField', 'BigIntegerField',
    'PositiveIntegerField', 'SmallIntegerField',
})


def check_field_size(value, max_size: int, field_name: str):
    """Raise ValueError if serialized field exceeds max_size bytes."""
    size = len(json.dumps(value).encode('utf-8'))
    if size > max_size:
        raise ValueError(f"{field_name} exceeds maximum size of {max_size} bytes")


def deep_merge_dict(a: dict, b: dict) -> dict:
    """Recursively merge dict b into dict a (in place) and return a."""
    for k, v in (b or {}).items():
        if isinstance(v, dict) and isinstance(a.get(k), dict):
            deep_merge_dict(a[k], v)
        else:
            a[k] = v
    return a


def _normalize_envelope(field_data) -> dict:
    """Normalize field payload into operation envelope {mode, value}."""
    if not isinstance(field_data, dict):
        return {'mode': 'update', 'value': field_data}
    if 'mode' in field_data or 'task' in field_data:
        return field_data
    return {'mode': 'update', 'value': field_data}


def _sanitize_empty_numeric(value, model_cls, field_name):
    """Convert empty string to None for numeric model fields."""
    if value != '' and value != "":
        return value
    try:
        model_field = model_cls._meta.get_field(field_name)
        if type(model_field).__name__ in NUMERIC_FIELD_NAMES:
            return None
    except Exception:
        pass
    return value


def _delete_field(obj, field: str):
    """Handle delete mode for a field — model attribute or prefs.userdefined."""
    if '.' in field:
        delete_nested_value(obj, field)
        return

    if hasattr(obj, field):
        setattr(obj, field, None)
        return

    # Check prefs.userdefined
    try:
        prefs = getattr(obj, 'prefs', {}) or {}
        if isinstance(prefs, str):
            try:
                prefs = json.loads(prefs)
            except json.JSONDecodeError:
                prefs = {}
        userdefined = prefs.get('userdefined', {})
        if field in userdefined:
            del userdefined[field]
            setattr(obj, 'prefs', prefs)
    except Exception:
        pass


def _set_fk_field(obj, field: str, model_field, value) -> bool:
    """Handle FK field assignment. Returns True if handled."""
    if not isinstance(model_field, (models.ForeignKey, models.OneToOneField)):
        return False

    id_attr = field if field.endswith('_id') else f'{field}_id'
    if isinstance(value, int) or (isinstance(value, str) and value.strip().isdigit()):
        setattr(obj, id_attr, int(value) if isinstance(value, str) else value)
        return True
    if value is None:
        setattr(obj, id_attr, None)
        return True
    return False


def _coerce_int_field(value, model_field):
    """Coerce string values to int for integer model fields."""
    if not isinstance(model_field, INT_FIELD_TYPES):
        return value
    if isinstance(value, str):
        m = re.search(r"(\d+)", value)
        if m:
            try:
                return int(m.group(1))
            except Exception:
                return 0
        return 0
    if value is None:
        return 0
    return value


def _store_unknown_field(obj, field: str, value, field_size_errors: list):
    """Route unknown fields to prefs.userdefined."""
    try:
        prefs = getattr(obj, 'prefs', {}) or {}
        if isinstance(prefs, str):
            try:
                prefs = json.loads(prefs)
            except json.JSONDecodeError:
                prefs = {}
        userdefined = prefs.setdefault('userdefined', {})
        storable = value
        try:
            raw_json = json.dumps(storable)
            if len(raw_json.encode('utf-8')) > MAX_FIELD_SIZE:
                storable = str(storable)[:UNKNOWN_FIELD_MAX_CHARS]
        except Exception:
            storable = str(storable)[:UNKNOWN_FIELD_MAX_CHARS]
        userdefined[field] = storable
        check_field_size(prefs, MAX_FIELD_SIZE, 'prefs')
        setattr(obj, 'prefs', prefs)
    except ValueError as e:
        field_size_errors.append(str(e))


def assign_fields(
    obj,
    data: dict,
    model_cls: type,
    json_field_names: set,
    m2m_field_names: set,
) -> dict:
    """Assign fields from data dict to model instance.

    Returns dict with:
        raw_password: str | None
        field_size_errors: list[str]
        field_value_errors: list[str]
    """
    field_size_errors: list[str] = []
    field_value_errors: list[str] = []
    raw_password = None

    for field, field_data in data.items():
        # Password handling
        if field == 'password':
            if isinstance(field_data, dict) and 'value' in field_data:
                raw_password = field_data['value']
            else:
                raw_password = field_data
            continue

        if field in SKIP_FIELDS or field in m2m_field_names:
            continue

        # Normalize to operation envelope
        field_data = _normalize_envelope(field_data)

        mode = field_data.get('mode') or field_data.get('task') or 'update'
        value = field_data.get('value')

        # Sanitize empty strings for numeric fields
        value = _sanitize_empty_numeric(value, model_cls, field)
        field_data['value'] = value

        if mode not in ('update', 'insert', 'delete'):
            continue

        if mode == 'delete':
            _delete_field(obj, field)
            continue

        if value is None:
            continue

        # Check size
        try:
            check_field_size(value, MAX_FIELD_SIZE, field)
        except ValueError as e:
            field_size_errors.append(str(e))
            continue

        try:
            if '.' in field or '[' in field:
                from apps.core.services.json_ops import apply_json_op
                apply_json_op(obj, field, mode, value, key=field_data.get('key'))
            else:
                # Check if it's a real model field
                try:
                    model_cls._meta.get_field(field)
                    _is_model_field = True
                except Exception:
                    _is_model_field = False

                if _is_model_field:
                    current = getattr(obj, field)
                    is_json_field = field in json_field_names or isinstance(current, dict)

                    # i18n wrapping
                    if is_json_field and field in _i18n_field_set and isinstance(value, str):
                        value = {'en': value}

                    if isinstance(value, dict) and is_json_field:
                        if isinstance(current, str):
                            try:
                                current = json.loads(current)
                            except json.JSONDecodeError:
                                current = {}
                        if not isinstance(current, dict):
                            current = {}
                        setattr(obj, field, deep_merge_dict(current, value))
                    elif is_json_field and not isinstance(value, (dict, list)) and value is not None:
                        console_logger.warning(
                            f"[SAVE] Skipping corrupted JSON field '{field}': "
                            f"got {type(value).__name__}, expected dict/list"
                        )
                        continue
                    else:
                        # FK and int coercion
                        try:
                            model_field = model_cls._meta.get_field(field)
                            if _set_fk_field(obj, field, model_field, value):
                                continue
                            value = _coerce_int_field(value, model_field)
                        except Exception:
                            pass
                        setattr(obj, field, value)
                else:
                    _store_unknown_field(obj, field, value, field_size_errors)

        except (ValueError, TypeError) as e:
            field_value_errors.append(f"{field}: {e}")
            continue

    return {
        'raw_password': raw_password,
        'field_size_errors': field_size_errors,
        'field_value_errors': field_value_errors,
    }
