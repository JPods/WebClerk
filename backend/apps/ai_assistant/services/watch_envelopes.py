"""Schema audit -- Alice checks JSON envelopes against Pydantic schemas.

Run periodically (nightly or weekly) to find fields in actual data that
aren't defined in the Pydantic schema. Logs questions via log_schema_question().

Usage:
    from apps.ai_assistant.services.watch_envelopes import audit_model_schemas
    results = audit_model_schemas(limit_per_model=10)
"""
from __future__ import annotations

import logging
from typing import Any

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
    from apps.core.constants.model_registry import MODEL_REGISTRY
    from common.schemas.defaults import schema_classes

    results = {}
    errors = {}
    total_questions = 0

    for model_key in (model_names or sorted(MODEL_REGISTRY)):
        # A model that cannot be checked is a finding, never a silent skip.
        try:
            envelope_schemas = schema_classes(model_key)
            app_model = MODEL_REGISTRY[model_key].import_model()
            sample = list(app_model.objects.order_by('-dt_modified')[:limit_per_model])
        except Exception as e:
            errors[model_key] = f'{type(e).__name__}: {e}'
            log_schema_question(
                model_name=model_key,
                question=f'Cannot audit {model_key} envelopes',
                detail=errors[model_key][:500],
            )
            total_questions += 1
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
        'errors': errors,
    }
