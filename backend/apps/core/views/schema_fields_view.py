"""
/wcapi/_pjpv_fields/ — Serve Pydantic schema metadata to React (PJPV Layer 2).

Returns field metadata derived from Pydantic schemas: type, label,
description, widget, precision, readonly, validation (min/max).

React fetches this instead of hardcoding labels and formatting.
One source of truth — the Pydantic schema — drives both backend and frontend.

Usage:
    GET /wcapi/_pjpv_fields/?model=invoice&envelope=totals
    GET /wcapi/_pjpv_fields/?envelope=totals    (all models)
    GET /wcapi/_pjpv_fields/                     (full catalog)
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny


class SchemaFieldsView(APIView):
    """Serve Pydantic schema field metadata to the frontend.

    Public — read-only schema metadata, no business data.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        envelope = request.query_params.get('envelope')

        try:
            from common.schemas.transaction_envelopes import (
                ENVELOPE_SCHEMA_MAP,
                schema_to_leaf_behaviors,
            )
        except ImportError:
            return Response({'error': 'Schema module not available'}, status=500)

        if envelope:
            schema_cls = ENVELOPE_SCHEMA_MAP.get(envelope)
            if not schema_cls:
                return Response(
                    {'error': f'Unknown envelope: {envelope}',
                     'available': list(ENVELOPE_SCHEMA_MAP.keys())},
                    status=404,
                )
            fields = _schema_to_fields(schema_cls)
            return Response({
                'envelope': envelope,
                'fields': fields,
            })

        # Full catalog — all envelope schemas
        catalog = {}
        for env_name, schema_cls in ENVELOPE_SCHEMA_MAP.items():
            catalog[env_name] = _schema_to_fields(schema_cls)

        return Response({'envelopes': catalog})


def _schema_to_fields(schema_cls):
    """Convert a Pydantic schema class to a frontend-consumable field dict.

    Returns: {field_name: {type, label, description, widget, precision,
              readonly, min, max}, ...}
    """
    fields = {}
    for name, field_info in schema_cls.model_fields.items():
        extra = field_info.json_schema_extra or {}
        entry = {
            'type': _pydantic_type_to_js(field_info.annotation),
            'label': field_info.title or name,
            'widget': extra.get('widget', 'text'),
        }
        if field_info.description:
            entry['description'] = field_info.description
        if 'precision' in extra:
            entry['precision'] = extra['precision']
        if extra.get('readonly'):
            entry['readonly'] = True

        # Validation constraints from Pydantic metadata
        for constraint in (field_info.metadata or []):
            if hasattr(constraint, 'ge') and constraint.ge is not None:
                entry['min'] = constraint.ge
            if hasattr(constraint, 'le') and constraint.le is not None:
                entry['max'] = constraint.le

        fields[name] = entry
    return fields


def _pydantic_type_to_js(annotation) -> str:
    """Map Python/Pydantic type annotations to JS type names."""
    import typing
    origin = getattr(annotation, '__origin__', None)

    # Handle Optional[X]
    if origin is typing.Union:
        args = [a for a in annotation.__args__ if a is not type(None)]
        if args:
            return _pydantic_type_to_js(args[0])

    type_map = {
        float: 'number',
        int: 'integer',
        str: 'string',
        bool: 'boolean',
    }
    return type_map.get(annotation, 'string')
