"""Schema audit -- Alice checks JSON envelopes against Pydantic schemas.

Run periodically (nightly or weekly) to find fields in actual data that
aren't defined in the Pydantic schema. Logs questions via log_schema_question().

Usage:
    from apps.ai_assistant.services.schema_audit import audit_model_schemas
    results = audit_model_schemas(limit_per_model=10)
"""
from __future__ import annotations

import importlib
import logging
from typing import Any

from django.apps import apps as dj_apps

logger = logging.getLogger(__name__)


def _get_schema_fields(schema_class) -> set:
    """Extract field names from a Pydantic BaseModel class."""
    if hasattr(schema_class, 'model_fields'):  # Pydantic v2
        return set(schema_class.model_fields.keys())
    if hasattr(schema_class, '__fields__'):  # Pydantic v1
        return set(schema_class.__fields__.keys())
    return set()


def _check_envelope(record_data: dict, schema_fields: set, envelope_name: str) -> list[str]:
    """Compare actual JSON keys against schema fields. Return unknown keys."""
    if not isinstance(record_data, dict):
        return []
    return [k for k in record_data.keys() if k not in schema_fields]


def audit_model_schemas(model_names: list[str] | None = None, limit_per_model: int = 10) -> dict:
    """Audit JSON envelopes for all (or specified) models.

    Samples recent records and checks config/metadata/refs/prefs against
    their Pydantic schemas. Logs questions for unknown fields.

    Returns summary dict.
    """
    from apps.ai_assistant.services.user_patterns import log_schema_question
    from apps.core.models import Setting

    # Get model definition settings (wc:model preferred, fall back to legacy wc:schema_map)
    settings_qs = Setting.objects.filter(purpose='wc:model', is_active=True)
    if model_names:
        settings_qs = settings_qs.filter(parent_model__in=model_names)
    if not settings_qs.exists():
        settings_qs = Setting.objects.filter(purpose='wc:schema_map', is_active=True)
        if model_names:
            settings_qs = settings_qs.filter(parent_model__in=model_names)

    results = {}
    total_questions = 0

    for setting in settings_qs:
        model_key = setting.parent_model
        cfg = setting.config or {}
        # wc:model stores schema under 'schema' key; legacy stores at top level
        schema_cfg = cfg.get('schema', cfg) if setting.purpose == 'wc:model' else cfg
        schema_module_path = schema_cfg.get('pydantic_schema', '')
        if not schema_module_path:
            continue

        # Try to import the schema module
        try:
            mod = importlib.import_module(schema_module_path)
        except ImportError:
            log_schema_question(
                model_name=model_key,
                question=f'Schema module {schema_module_path} not found',
                detail=f'Setting id={setting.pk} references a missing module',
            )
            total_questions += 1
            continue

        # Get schema classes for each envelope
        envelope_schemas = {}
        for envelope in ['config', 'metadata', 'prefs', 'refs']:
            class_name = cfg.get(f'{envelope}_schema', '')
            if class_name and hasattr(mod, class_name):
                envelope_schemas[envelope] = getattr(mod, class_name)

        if not envelope_schemas:
            continue

        # Get the Django model
        from apps.core.constants.model_registry import get_model_meta
        meta = get_model_meta(model_key)
        if not meta:
            continue

        try:
            parts = meta.model_class.rsplit('.', 1)
            app_model = dj_apps.get_model(
                parts[0].replace('apps.', '').split('.')[0],
                parts[1]
            )
        except Exception:
            continue

        # Sample recent records
        try:
            sample = app_model.objects.order_by('-dt_modified')[:limit_per_model]
        except Exception:
            continue

        model_questions = 0
        seen_fields = set()

        for record in sample:
            for envelope, schema_cls in envelope_schemas.items():
                data = getattr(record, envelope, None)
                if not isinstance(data, dict):
                    continue
                schema_fields = _get_schema_fields(schema_cls)
                if not schema_fields:
                    continue
                unknown = _check_envelope(data, schema_fields, envelope)
                for field in unknown:
                    field_key = f'{model_key}.{envelope}.{field}'
                    if field_key in seen_fields:
                        continue
                    seen_fields.add(field_key)
                    log_schema_question(
                        model_name=model_key,
                        question=f'Unknown field in .{envelope}: {field}',
                        detail=f'Field "{field}" found in {model_key}.{envelope} but not in {schema_cls.__name__}',
                        field=f'{envelope}.{field}',
                        observed_value=str(type(data[field]).__name__),
                    )
                    model_questions += 1

        results[model_key] = model_questions
        total_questions += model_questions

    return {
        'models_audited': len(results),
        'total_questions': total_questions,
        'by_model': {k: v for k, v in results.items() if v > 0},
    }
