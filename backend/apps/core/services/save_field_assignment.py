"""Field assignment service for the universal save pipeline.

Extracted from save_view.py — handles field coercion, JSON deep merge,
FK normalization and mode dispatch (update/insert/delete). A field the model does not
have is never stored: the one field authority ignores anything not enumerated (Bill,
2026-09-20), so the old capture into prefs.userdefined was deleted (Bill, 2026-09-24:
"Delete junk").

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
# The userdefined bounds live with the envelope that defines the bag.
from common.schemas.envelopes import USERDEFINED_KEY_MAX_LEN, USERDEFINED_VALUE_MAX_LEN  # noqa: E402
MAX_MERGE_DEPTH = 8                 # max recursion depth for deep_merge_dict
MAX_DOT_PATH_DEPTH = 8             # max segments in a dot-path field name

# Models whose fields may contain binary/document content
BINARY_ALLOWED_MODELS = frozenset({'document'})
BINARY_ALLOWED_FIELDS = frozenset({'path'})

SKIP_FIELDS = frozenset({
    'model_name', 'id', 'version',       # model_name: the internal save_record convention;
                                         # a client sending it is refused at the REST view
    'bulk', 'lines', 'uuid', 'options',
})

# A key that is not a field is refused with coaching, never dropped (Bill, 2026-09-25): a
# silent drop returned success for every UI save sent in a `record` wrapper and blanked every
# card sent with a retired alias. These two get their own coaching.
WRAPPER_COACHING = {
    w: "send the fields flat in the body — the model and the id are the path "
       "(PUT /wcapi/<model>/<id>/)" for w in ('record', 'data')
}

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


def _check_json_depth(obj, depth: int = 0) -> int:
    """Return max nesting depth of a dict/list structure."""
    if depth >= MAX_MERGE_DEPTH:
        return depth
    if isinstance(obj, dict):
        if not obj:
            return depth
        return max(_check_json_depth(v, depth + 1) for v in obj.values())
    if isinstance(obj, list):
        if not obj:
            return depth
        return max(_check_json_depth(v, depth + 1) for v in obj)
    return depth


def deep_merge_dict(a: dict, b: dict, _depth: int = 0) -> dict:
    """Recursively merge dict b into dict a (in place) and return a.

    Raises ValueError if incoming data or merge depth exceeds MAX_MERGE_DEPTH
    to prevent stack overflow from crafted payloads.
    """
    if _depth >= MAX_MERGE_DEPTH:
        raise ValueError(
            f"JSON merge depth exceeds {MAX_MERGE_DEPTH} levels"
        )
    for k, v in (b or {}).items():
        if isinstance(v, dict) and isinstance(a.get(k), dict):
            deep_merge_dict(a[k], v, _depth + 1)
        else:
            # Check depth of incoming value before assigning
            if isinstance(v, (dict, list)):
                incoming_depth = _check_json_depth(v)
                if _depth + incoming_depth >= MAX_MERGE_DEPTH:
                    raise ValueError(
                        f"JSON nesting depth exceeds {MAX_MERGE_DEPTH} levels"
                    )
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
    """Handle delete mode for a field — a model attribute or a dotted leaf."""
    if '.' in field:
        delete_nested_value(obj, field)
        return

    if hasattr(obj, field):
        setattr(obj, field, None)
        return



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


def _coerce_number_field(value, model_cls, field):
    """A decimal or float sent as text ("100.00", as JSON clients often send money) becomes
    the number the field holds; text that is not a number is a field error, not a crash in
    the model's save."""
    if not isinstance(value, str):
        return value
    try:
        model_field = model_cls._meta.get_field(field)
    except Exception:  # noqa: BLE001 — not a column; left as it came
        return value
    if not isinstance(model_field, (models.DecimalField, models.FloatField)):
        return value
    from django.core.exceptions import ValidationError
    try:
        return model_field.to_python(value.strip() or None)
    except ValidationError as e:
        raise ValueError(f'{value!r} is not a number') from e


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


def _check_binary_content(value, field: str, model_name: str) -> str | None:
    """Return error message if value contains binary/base64 content
    in a field that doesn't allow it. Documents go through Document.path ONLY."""
    if model_name in BINARY_ALLOWED_MODELS and field in BINARY_ALLOWED_FIELDS:
        return None
    if isinstance(value, str):
        from common.schemas.envelopes import looks_like_binary
        if looks_like_binary(value):
            return (
                f"binary/base64 content not allowed in {field} — "
                f"use Document.path for file storage"
            )
    return None


def assign_fields(
    obj,
    data: dict,
    model_cls: type,
    json_field_names: set,
    m2m_field_names: set,
    model_name: str = '',
) -> dict:
    """Assign fields from data dict to model instance.

    Returns dict with:
        raw_password: str | None
        field_size_errors: list[str]
        field_value_errors: list[str]
    """
    field_size_errors: list[str] = []
    field_value_errors: list[str] = []
    unknown_fields: list[str] = []
    raw_password = None
    _model_name_lower = (model_name or '').lower()

    for field, field_data in data.items():
        # Password handling
        if field == 'password':
            if isinstance(field_data, dict) and 'value' in field_data:
                raw_password = field_data['value']
            else:
                raw_password = field_data
            continue

        # An underscore key is a signal to the hooks, never a field (the underscore rule).
        if field in SKIP_FIELDS or field in m2m_field_names or field.startswith('_'):
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

        # Reject binary/base64 content outside Document.path
        binary_err = _check_binary_content(value, field, _model_name_lower)
        if binary_err:
            field_size_errors.append(binary_err)
            continue

        # Check size
        try:
            check_field_size(value, MAX_FIELD_SIZE, field)
        except ValueError as e:
            field_size_errors.append(str(e))
            continue

        try:
            if '.' in field or '[' in field:
                # Guard: reject paths deeper than MAX_DOT_PATH_DEPTH
                _parts = field.split('.')
                if len(_parts) > MAX_DOT_PATH_DEPTH:
                    field_size_errors.append(
                        f"dot-path '{field[:40]}...' exceeds "
                        f"{MAX_DOT_PATH_DEPTH} segments"
                    )
                    continue

                # Guard: reject nested writes into userdefined via dot-path
                # e.g. "prefs.userdefined.foo.bar" or "metadata.userdefined.x.y"
                try:
                    _ud_idx = _parts.index('userdefined')
                    # Allow "prefs.userdefined.key" (depth 1) but reject
                    # "prefs.userdefined.key.nested" (depth 2+)
                    if len(_parts) > _ud_idx + 2:
                        field_size_errors.append(
                            f"userdefined nesting forbidden: '{field}' — "
                            f"only flat key:value pairs allowed"
                        )
                        continue
                    # Also enforce scalar-only and limits on the value
                    if len(_parts) == _ud_idx + 2:
                        _ud_key = _parts[_ud_idx + 1]
                        if len(_ud_key) > USERDEFINED_KEY_MAX_LEN:
                            field_size_errors.append(
                                f"userdefined key '{_ud_key[:20]}...' exceeds "
                                f"{USERDEFINED_KEY_MAX_LEN} chars"
                            )
                            continue
                        if isinstance(value, (dict, list)):
                            field_size_errors.append(
                                f"userdefined['{_ud_key}'] must be a flat scalar, "
                                f"got {type(value).__name__}"
                            )
                            continue
                        if isinstance(value, str) and len(value) > USERDEFINED_VALUE_MAX_LEN:
                            field_size_errors.append(
                                f"userdefined['{_ud_key}'] string exceeds "
                                f"{USERDEFINED_VALUE_MAX_LEN} chars"
                            )
                            continue
                except ValueError:
                    pass  # 'userdefined' not in path — normal dot-path, proceed

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
                        value = _coerce_number_field(value, model_cls, field)
                        # If a property shadows the DB column, write to __dict__
                        # directly so obj.save() persists the value.
                        if isinstance(getattr(type(obj), field, None), property):
                            obj.__dict__[field] = value
                        else:
                            setattr(obj, field, value)
                else:
                    unknown_fields.append(_coach_unknown(field, model_cls, json_field_names))
                    continue

        except (ValueError, TypeError) as e:
            field_value_errors.append(f"{field}: {e}")
            continue

    return {
        'raw_password': raw_password,
        'field_size_errors': field_size_errors,
        'field_value_errors': field_value_errors,
        'unknown_fields': unknown_fields,
    }


def _coach_unknown(field: str, model_cls, json_field_names: set) -> str:
    """'action_en: not a field of action — did you mean action.en?' The nearest real name:
    a retired i18n alias (<field>_<lang>) maps to <field>.<lang>; otherwise the closest field."""
    import difflib
    if field in WRAPPER_COACHING:                    # only reached when not a real field
        return f"{field}: {WRAPPER_COACHING[field]}"
    names = [f.name for f in model_cls._meta.concrete_fields]
    label = getattr(model_cls._meta, 'model_name', 'this model')
    base, _, lang = field.rpartition('_')
    if base in json_field_names and len(lang) == 2:
        hint = f"{base}.{lang}"
    else:
        close = difflib.get_close_matches(field, names, n=1, cutoff=0.6)
        hint = close[0] if close else None
    return f"{field}: not a field of {label}" + (f" — did you mean {hint}?" if hint else "")
