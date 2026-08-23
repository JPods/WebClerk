"""
SystemDispatchView — single entry point for all _ prefixed system endpoints.

URL: wcapi/_<str:action>/
Convention: _ prefix = system plumbing (React-to-WC3 metadata), not data.

Adding a new system endpoint:
  1. Add entry to ACTIONS dict: 'my_action': '_handle_my_action'
  2. Add method: def _handle_my_action(self, request): ...
  3. URL is automatically wcapi/_my_action/ — no urls.py changes needed.

See: readmes/topics/architecture/wcapi-system-endpoints.md
"""
import logging

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated

logger = logging.getLogger(__name__)


class SystemDispatchView(APIView):
    """Dispatch system plumbing requests by action name.

    All actions under wcapi/_<action>/ route through here.
    Public actions (schema metadata, health) use AllowAny.
    Protected actions check auth in the handler.
    """
    # Default to public — individual handlers can check auth if needed
    permission_classes = [AllowAny]

    # ── Action registry ────────────────────────────────────────────
    # key = URL action (wcapi/_<key>/), value = method name
    ACTIONS = {
        'pjpv_fields': '_handle_pjpv_fields',
        'pjpv_envelopes': '_handle_pjpv_envelopes',
    }

    def get(self, request, action):
        handler_name = self.ACTIONS.get(action)
        if not handler_name:
            return Response({
                'error': f'Unknown system action: _{action}',
                'available': [f'_{k}' for k in self.ACTIONS.keys()],
            }, status=404)

        handler = getattr(self, handler_name, None)
        if not handler:
            logger.error("SystemDispatch: action '%s' registered but method '%s' not found", action, handler_name)
            return Response({'error': 'Handler not implemented'}, status=500)

        return handler(request)

    # ── Handlers ───────────────────────────────────────────────────

    def _handle_pjpv_fields(self, request):
        """Serve Pydantic schema field metadata to React.

        GET /wcapi/_pjpv_fields/                  → full catalog (all envelopes)
        GET /wcapi/_pjpv_fields/?envelope=totals  → single envelope
        """
        try:
            from common.schemas.transaction_envelopes import ENVELOPE_SCHEMA_MAP
        except ImportError:
            return Response({'error': 'Schema module not available'}, status=500)

        envelope = request.query_params.get('envelope')

        if envelope:
            schema_cls = ENVELOPE_SCHEMA_MAP.get(envelope)
            if not schema_cls:
                return Response({
                    'error': f'Unknown envelope: {envelope}',
                    'available': list(ENVELOPE_SCHEMA_MAP.keys()),
                }, status=404)
            return Response({
                'envelope': envelope,
                'fields': _schema_to_fields(schema_cls),
            })

        # Full catalog
        catalog = {}
        for env_name, schema_cls in ENVELOPE_SCHEMA_MAP.items():
            catalog[env_name] = _schema_to_fields(schema_cls)

        return Response({'envelopes': catalog})

    def _handle_pjpv_envelopes(self, request):
        """List available envelope schemas and their field counts.

        GET /wcapi/_pjpv_envelopes/
        """
        try:
            from common.schemas.transaction_envelopes import (
                ENVELOPE_SCHEMA_MAP, ITEM_SCHEMA_MAP, AUXILIARY_SCHEMA_MAP,
            )
        except ImportError:
            return Response({'error': 'Schema module not available'}, status=500)

        def _summarize(schema_map, category):
            return {
                name: {
                    'fields': len(cls.model_fields),
                    'category': category,
                }
                for name, cls in schema_map.items()
            }

        return Response({
            'transaction': _summarize(ENVELOPE_SCHEMA_MAP, 'transaction'),
            'item': _summarize(ITEM_SCHEMA_MAP, 'item'),
            'auxiliary': _summarize(AUXILIARY_SCHEMA_MAP, 'auxiliary'),
            'total_schemas': (
                len(ENVELOPE_SCHEMA_MAP) + len(ITEM_SCHEMA_MAP) + len(AUXILIARY_SCHEMA_MAP)
            ),
        })


# ── Shared helpers ─────────────────────────────────────────────────

def _schema_to_fields(schema_cls):
    """Convert a Pydantic schema class to a frontend-consumable field dict."""
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
