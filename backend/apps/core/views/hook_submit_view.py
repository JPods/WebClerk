"""Inbound hook review request — the WCHQ end of the exchange.

An instance submits a hook; this view works it immediately (structure, simulated
test runs, Athena, Allie, Claude) and answers in the same response when everything
is clean. When any adviser has a question, the review is held at WCHQ for a person
to sign off, and the instance gets an ack instead.

Only an installation running as WCHQ answers here (`WC_IS_HQ`). Everywhere else the
endpoint refuses, so an ordinary instance cannot be talked into signing its own
hooks.
"""
import json
import logging

from decouple import config
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from apps.core.views.hook_clearance_view import _validate_athena

logger = logging.getLogger(__name__)

IS_HQ = config('WC_IS_HQ', default='false').lower() in ('true', '1', 'yes')


@method_decorator(csrf_exempt, name='dispatch')
class HookSubmitView(View):
    """POST a hook.review.request payload."""

    def post(self, request):
        if not IS_HQ:
            return JsonResponse({'error': 'This installation is not WCHQ'}, status=404)

        _connection, denied = _validate_athena(request)
        if denied:
            return denied

        try:
            payload = json.loads(request.body or b'{}')
        except ValueError:
            return JsonResponse({'error': 'Body must be JSON'}, status=400)

        if payload.get('kind') not in (None, 'hook.review.request'):
            return JsonResponse({'error': 'Not a hook review request'}, status=400)
        if not payload.get('hooks') or not payload.get('report_ida'):
            return JsonResponse({'error': 'hooks and report_ida are required'}, status=400)

        from apps.ai_assistant.services.hook_review_hq import review_request
        answer = review_request(payload)

        if answer.get('status') == 'error':
            return JsonResponse(answer, status=400)
        # 202: received and being looked at by a person.
        status = 202 if answer.get('status') == 'held' else 200
        return JsonResponse(answer, status=status)
