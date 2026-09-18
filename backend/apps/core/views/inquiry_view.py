"""Public inquiry form → Action.

POST /wcapi/_inquiry/  {name, email, organization?, topic?, message, page?, website?}

No login. Writes one Action (action_type='inquiry', Backlog) and nothing else — no
Contact is created from unverified input. Accepted fields only; lengths capped;
5 per hour per IP; `website` is a honeypot a person never sees.

Next step (when Andi can send mail): email a signed link, open the form from it,
and set config.inquiry.email_verified.
"""
from __future__ import annotations

import logging

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.utils import timezone
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.core.models import Action
from common.schemas.defaults import schema_classes

logger = logging.getLogger(__name__)

LIMITS = {'name': 120, 'email': 254, 'organization': 120, 'topic': 80, 'page': 200, 'message': 4000}
REQUIRED = ('name', 'email', 'message')


class InquiryView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []          # anonymous: no session, so no CSRF coupling
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'inquiry'

    def post(self, request):
        data = request.data
        if str(data.get('website') or '').strip():
            return Response({'ok': True})    # honeypot filled: a bot. Look accepted, keep nothing.

        fields = {k: str(data.get(k) or '').strip() for k in LIMITS}
        errors = {k: 'required' for k in REQUIRED if not fields[k]}
        errors.update({k: f'at most {n} characters' for k, n in LIMITS.items() if len(fields[k]) > n})
        if fields['email'] and 'email' not in errors:
            try:
                validate_email(fields['email'])
            except ValidationError:
                errors['email'] = 'not a valid email address'
        if errors:
            return Response({'ok': False, 'errors': errors}, status=400)

        inquiry = {k: fields[k] for k in ('name', 'email', 'organization', 'topic', 'page')}
        config = {'inquiry': {**inquiry, 'email_verified': False}}
        metadata = {'source': {'type': 'web_inquiry'}}
        classes = schema_classes('action')
        classes['config'].model_validate(config)
        classes['metadata'].model_validate(metadata)

        now = timezone.now()
        topic = fields['topic'] or 'Inquiry'
        action = Action.objects.create(
            ida=f"INQ-{now.strftime('%Y%m%dT%H%M%S')}",
            status='open',
            kanban_column='Backlog',
            action_type='inquiry',
            priority=2,
            action={'en': f"{topic}: {fields['name']}"[:200]},
            description={'en': fields['message']},
            config=config,
            metadata=metadata,
        )
        logger.info('[INQUIRY] action %s from %s (%s)', action.pk, fields['email'], fields['page'])
        return Response({'ok': True, 'reference': action.ida})
