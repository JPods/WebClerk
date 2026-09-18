"""Inbound WCHQ message for a hook review — ack, answer or revoke.

The message is handed to Alice (ai_assistant.services.hook_review.receive), who
owns both ends of this exchange. The token is verified locally against the stored
hooks, so this endpoint grants nothing on its own — a wrong token changes nothing.

Authorization reuses the Athena token on the Connection records, the same secret
the instance-submit endpoint trusts.
"""
import json
import logging

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from apps.sync.services.athena_auth import validate_athena as _validate_athena

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class HookClearanceView(View):
    """POST {"report_ida": "...", "hook_hash": "...", "token": "..."}"""

    def post(self, request):
        _connection, denied = _validate_athena(request)
        if denied:
            return denied

        try:
            payload = json.loads(request.body or b'{}')
        except ValueError:
            return JsonResponse({'error': 'Body must be JSON'}, status=400)

        from apps.ai_assistant.services.hook_review import receive
        answer = receive(payload)
        if not answer.get('ok'):
            logger.warning('[HOOK] WCHQ message refused: %s', answer)
            return JsonResponse(answer, status=400)

        logger.info('[HOOK] %s → %s', payload.get('report_ida'), answer.get('status'))
        return JsonResponse(answer, status=200)
