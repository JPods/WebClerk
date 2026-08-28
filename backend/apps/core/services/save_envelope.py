"""Envelope validation service for the universal save pipeline.

Validates JSON envelope fields (metadata, config, refs, prefs) against
their Pydantic schemas before write. Front-end validation handles good
behavior; this handles bad actors.

Uses the schema registry in Setting(purpose='wc:model').config.schema
to look up the correct Pydantic class for each model + envelope field.

Part of the save_* service cluster:
  save_field_assignment.py  — field coercion, JSON merge
  save_line_processing.py   — line CRUD for header models
  save_envelope.py          — this file
"""
from __future__ import annotations

import importlib
import logging
from typing import Any

from pydantic import ValidationError as PydanticValidationError

logger = logging.getLogger(__name__)

# Envelope fields and their schema_map keys
ENVELOPE_FIELDS = {
    'metadata': 'metadata_schema',
    'config': 'config_schema',
    'refs': 'refs_schema',
    'prefs': 'prefs_schema',
}

# Cache: model_name → {field → Pydantic class}
_schema_cache: dict[str, dict[str, type]] = {}


def _load_schema_classes(model_name: str) -> dict[str, type]:
    """Load Pydantic schema classes for a model from the Setting registry.

    Returns dict mapping field name → Pydantic class.
    Caches after first lookup.
    """
    if model_name in _schema_cache:
        return _schema_cache[model_name]

    result: dict[str, type] = {}

    try:
        from apps.core.models.setting import Setting
        setting = Setting.objects.filter(
            purpose='wc:model',
            parent_model=model_name,
        ).first()

        if not setting:
            _schema_cache[model_name] = result
            return result

        schema_config = (setting.config or {}).get('schema', {})
        module_path = schema_config.get('pydantic_schema', '')

        if not module_path:
            _schema_cache[model_name] = result
            return result

        mod = importlib.import_module(module_path)

        for field_name, schema_key in ENVELOPE_FIELDS.items():
            class_name = schema_config.get(schema_key, '')
            if class_name:
                cls = getattr(mod, class_name, None)
                if cls is not None:
                    result[field_name] = cls

    except Exception as e:
        logger.warning(f"[SAVE_ENVELOPE] Failed to load schemas for {model_name}: {e}")

    _schema_cache[model_name] = result
    return result


def validate_envelope(
    obj,
    model_name: str,
    fields_written: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Validate envelope fields on a model instance against Pydantic schemas.

    Args:
        obj: Model instance (after field assignment, before save).
        model_name: Normalized model name (e.g. 'order', 'contact').
        fields_written: Set of field names that were written this save.
            If provided, only validates envelopes that were touched.
            If None, validates all envelopes.

    Returns:
        List of violation dicts: [{field, message, details}]
        Empty list = all valid.
    """
    schemas = _load_schema_classes(model_name)
    if not schemas:
        return []

    violations = []

    for field_name, schema_cls in schemas.items():
        # Skip envelopes that weren't touched this save (if tracking)
        if fields_written is not None and field_name not in fields_written:
            continue

        value = getattr(obj, field_name, None)
        if value is None or value == {}:
            continue

        if not isinstance(value, dict):
            violations.append({
                'field': field_name,
                'message': f'{field_name} must be a dict, got {type(value).__name__}',
                'details': {},
            })
            continue

        try:
            schema_cls.model_validate(value)
        except PydanticValidationError as e:
            for error in e.errors():
                loc = '.'.join(str(p) for p in error.get('loc', []))
                violations.append({
                    'field': f"{field_name}.{loc}" if loc else field_name,
                    'message': error.get('msg', 'Validation error'),
                    'details': {
                        'type': error.get('type', ''),
                        'input': str(error.get('input', ''))[:200],
                    },
                })

    return violations


def validate_and_reject(
    obj,
    model_name: str,
    fields_written: set[str] | None = None,
) -> str | None:
    """Validate envelopes; return error message string if invalid, None if ok.

    Convenience wrapper for save_view — call after field assignment,
    before obj.save(). Returns a single error string suitable for
    api_response(message=...).
    """
    violations = validate_envelope(obj, model_name, fields_written)
    if not violations:
        return None

    # Build human-readable message
    parts = []
    for v in violations[:5]:  # cap at 5 to avoid huge responses
        parts.append(f"{v['field']}: {v['message']}")
    msg = '; '.join(parts)
    if len(violations) > 5:
        msg += f' (+{len(violations) - 5} more)'

    logger.warning(f"[SAVE_ENVELOPE] {model_name} rejected: {msg}")
    return msg


def clear_cache():
    """Clear the schema class cache. Call after schema Setting changes."""
    _schema_cache.clear()
