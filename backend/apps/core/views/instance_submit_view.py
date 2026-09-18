"""Receive submissions from remote WC3 instances (issues, escalations).

Only active when WC_IS_HQ=true in .env. Otherwise returns 404.

Authentication: Authorization: Athena <token>
Validates against Connection records (encryption.athena_token).

POST /wcapi/instance/submit/
Body: { "model_name": "action", "record": { ... } }
"""
import json
import logging

from decouple import config
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from apps.sync.services.athena_auth import validate_athena as _validate_athena

logger = logging.getLogger(__name__)

IS_HQ = config('WC_IS_HQ', default='false').lower() in ('true', '1', 'yes')

# Models that remote instances are allowed to submit
ALLOWED_MODELS = {'action'}


@method_decorator(csrf_exempt, name='dispatch')
class InstanceSubmitView(View):
    """POST /wcapi/instance/submit/ — receive a record from a remote instance."""

    def post(self, request):
        if not IS_HQ:
            return JsonResponse({'error': 'Not found'}, status=404)

        connection, error_resp = _validate_athena(request)
        if error_resp:
            return error_resp

        try:
            body = json.loads(request.body.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        model_name = body.get('model_name', '')
        record = body.get('record', {})

        if model_name not in ALLOWED_MODELS:
            return JsonResponse(
                {'error': f'Model {model_name} not accepted'}, status=400
            )

        if not record:
            return JsonResponse({'error': 'Empty record'}, status=400)

        try:
            from apps.core.constants.model_registry import get_model
            ModelClass = get_model(model_name)
            if not ModelClass:
                return JsonResponse(
                    {'error': f'Model {model_name} not found'}, status=400
                )

            # Tag the record with the source connection
            metadata = record.get('metadata', {})
            if not isinstance(metadata, dict):
                metadata = {}
            metadata['source_connection'] = {
                'ida': connection.ida,
                'name': connection.name,
                'instance_uuid': (connection.config or {}).get('instance_uuid', ''),
            }
            record['metadata'] = metadata

            # Create the record
            instance = ModelClass()
            for field_name, value in record.items():
                if hasattr(instance, field_name):
                    setattr(instance, field_name, value)
            instance.save()

            logger.info(
                "[WCHQ] Instance submit: model=%s id=%s from=%s",
                model_name, instance.id, connection.ida,
            )

            return JsonResponse({
                'status': 'ok',
                'model_name': model_name,
                'id': instance.id,
                'uuid': str(getattr(instance, 'uuid', '')),
            }, status=201)

        except Exception as e:
            logger.exception("[WCHQ] Instance submit failed")
            return JsonResponse({'error': str(e)}, status=500)
