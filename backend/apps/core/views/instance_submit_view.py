"""Receive submissions from remote WC3 instances (issues, escalations).

Only active when WC_IS_HQ=true in .env. Otherwise returns 404.

Authentication: Authorization: Athena <token>
Validates against Connection records (encryption.athena_token).

POST /wcapi/instance/submit/
Body: { "model_name": "action", "record": { ... } }

Only the fields in ALLOWED_FIELDS are taken; the record is always inserted; a record carrying
metadata.source_instance.local_uuid already received from the same connection is not received
again.
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

# What a remote instance may set, per model. Nothing else is taken: not id, uuid or version
# (an id made an UPDATE of HQ's own row — FAULT 2026-11-01), not project_id (a number in the
# sender's database), not assigned_to or created_by (the sender's people).
ALLOWED_FIELDS = {
    'action': ('action', 'description', 'priority', 'kanban_column', 'action_type',
               'project_name', 'metadata'),
}
#: refs keys a remote instance may set — words, never links to records.
ALLOWED_REFS = ('tags', 'keywords')


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

        if model_name not in ALLOWED_FIELDS:
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

            metadata = record.get('metadata')
            metadata = dict(metadata) if isinstance(metadata, dict) else {}
            metadata['source_connection'] = {
                'ida': connection.ida,
                'name': connection.name,
                'instance_uuid': (connection.config or {}).get('instance_uuid', ''),
            }
            source_uuid = str((metadata.get('source_instance') or {}).get('local_uuid') or '')

            # The same record sent twice is received once.
            if source_uuid:
                seen = ModelClass.objects.filter(
                    metadata__source_connection__ida=connection.ida,
                    metadata__source_instance__local_uuid=source_uuid).first()
                if seen is not None:
                    return JsonResponse({'status': 'ok', 'model_name': model_name, 'id': seen.id,
                                         'uuid': str(seen.uuid), 'duplicate': True}, status=200)

            values = {k: record[k] for k in ALLOWED_FIELDS[model_name] if k in record}
            values['metadata'] = metadata
            refs = record.get('refs')
            if isinstance(refs, dict):
                values['refs'] = {k: refs[k] for k in ALLOWED_REFS if isinstance(refs.get(k), list)}
            instance = ModelClass(**values)
            instance.save(force_insert=True)

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
