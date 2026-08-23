"""Template resolution API — resolves {{model.field}} placeholders and discovers fields.

Endpoints:
  POST /wcapi/resolve-template/  — resolve placeholders against live records
  GET  /wcapi/template-fields/   — discover available fields per model
"""
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.core.services.template_resolver import resolve_template, get_template_fields

logger = logging.getLogger(__name__)


class ResolveTemplateView(APIView):
    """Resolve {{model.field}} placeholders in a template string.

    POST /wcapi/resolve-template/
    {
        "template": "Dear {{contact.name_first}}, your order {{order.ida}} totals {{order.totals.total}}.",
        "context": {"order": 29, "contact": 41}
    }

    Returns:
    {
        "resolved": "Dear Bill, your order DEV-29 totals 450.00.",
        "fields_used": ["contact.name_first", "order.ida", "order.totals.total"],
        "fields_missing": [],
        "context_models": ["order", "contact", "customer"]
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        template_str = request.data.get('template', '')
        context = request.data.get('context', {})

        if not template_str:
            return Response({
                'status': 'fail',
                'message': 'template is required',
                'data': None,
            }, status=400)

        if not isinstance(context, dict):
            return Response({
                'status': 'fail',
                'message': 'context must be a dict mapping model names to record IDs',
                'data': None,
            }, status=400)

        result = resolve_template(template_str, context)

        return Response({
            'status': 'success',
            'data': result,
        })


class TemplateFieldsView(APIView):
    """Discover available template fields for a model.

    GET /wcapi/template-fields/?model=order

    Returns fields, JSON subfields, related models, and example placeholders.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        model_name = request.query_params.get('model', '')
        if not model_name:
            return Response({
                'status': 'fail',
                'message': 'model query parameter is required (e.g. ?model=order)',
                'data': None,
            }, status=400)

        result = get_template_fields(model_name)
        if 'error' in result:
            return Response({
                'status': 'fail',
                'message': result['error'],
                'data': None,
            }, status=404)

        return Response({
            'status': 'success',
            'data': result,
        })
