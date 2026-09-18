"""Public inquiry → emailed link → form → Action.

1. POST /wcapi/_inquiry/start/  {email, topic?, page?, website?}
   Emails a signed link (24 h) to /tfm/inquiry.html?t=<token>. Writes nothing.
2. GET  /wcapi/_inquiry/?t=<token>
   The form page checks its link: {email, topic} or 400 (expired / tampered / used).
3. POST /wcapi/_inquiry/?t=<token>  {name, company, message, phone?, website?}
   (the link code rides in the URL, never the body: SecretGuard scans bodies, and the
   visitor's own text should still be scanned)
   Creates one Action (action_type='inquiry', Backlog). The email comes from the token,
   so it is proven; each token creates at most one Action.

No login, no Contact created. Accepted fields only, lengths capped, sending mail 5/hour per IP (the form 30/hour),
`website` is a honeypot a person never sees. If mail cannot be sent, the visitor is told —
nothing pretends to have worked.
"""
from __future__ import annotations

import hashlib
import logging

from django.conf import settings
from django.core import signing
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.validators import validate_email
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.core.models import Action
from common.schemas.defaults import schema_classes

logger = logging.getLogger(__name__)

SALT = 'wc-inquiry'
MAX_AGE = 24 * 60 * 60
FORM_PATH = '/tfm/inquiry.html'
LIMITS = {'name': 120, 'email': 254, 'phone': 40, 'company': 120, 'topic': 80, 'page': 200, 'message': 4000}


def _clean(data, keys):
    return {k: str(data.get(k) or '').strip() for k in keys}


def _too_long(fields):
    return {k: f'at most {LIMITS[k]} characters' for k, v in fields.items() if len(v) > LIMITS[k]}


def _read_token(token: str) -> dict:
    """Payload of a valid, unexpired, unused token. Raises ValueError with the reason."""
    try:
        payload = signing.loads(token, salt=SALT, max_age=MAX_AGE)
    except signing.SignatureExpired:
        raise ValueError('This link has expired — ask for a new one.')
    except signing.BadSignature:
        raise ValueError('This link is not valid — ask for a new one.')
    if Action.objects.filter(config__inquiry__token_id=_token_id(token)).exists():
        raise ValueError('This link has already been used.')
    return payload


def _token_id(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class _Public(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []          # anonymous: no session, so no CSRF coupling
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'inquiry'


class InquiryStartView(_Public):

    def post(self, request):
        if str(request.data.get('website') or '').strip():
            return Response({'ok': True})    # honeypot filled: a bot. Look accepted, send nothing.
        fields = _clean(request.data, ('email', 'topic', 'page'))
        errors = _too_long(fields)
        if not fields['email']:
            errors['email'] = 'required'
        elif 'email' not in errors:
            try:
                validate_email(fields['email'])
            except ValidationError:
                errors['email'] = 'That is not a valid email address.'
        if errors:
            return Response({'ok': False, 'errors': errors}, status=400)

        token = signing.dumps(fields, salt=SALT)
        link = request.build_absolute_uri(f'{FORM_PATH}?t={token}')
        topic = fields['topic'] or 'WebClerk'
        body = (
            f"Thank you for your interest in {topic}.\n\n"
            f"Open this link to tell us who you are and what you need. It works once, for 24 hours:\n\n"
            f"{link}\n\n"
            f"If you did not ask for this, ignore this email — nothing has been recorded.\n\n"
            f"WebClerk — open source commerce, locally governed.\n"
        )
        try:
            send_mail(f'Your {topic} form', body, settings.DEFAULT_FROM_EMAIL, [fields['email']])
        except Exception as e:
            logger.error('[INQUIRY] could not send link to %s: %s', fields['email'], e)
            return Response({'ok': False, 'errors': {'email': 'We could not send the email just now — please try again later.'}},
                            status=502)
        logger.info('[INQUIRY] link sent to %s (%s)', fields['email'], fields['page'])
        return Response({'ok': True})


class InquiryView(_Public):
    throttle_scope = 'inquiry_form'

    def get(self, request):
        try:
            payload = _read_token(str(request.query_params.get('t') or ''))
        except ValueError as e:
            return Response({'ok': False, 'errors': {'token': str(e)}}, status=400)
        return Response({'ok': True, 'email': payload['email'], 'topic': payload.get('topic', '')})

    def post(self, request):
        if str(request.data.get('website') or '').strip():
            return Response({'ok': True})
        token = str(request.query_params.get('t') or '')
        try:
            payload = _read_token(token)
        except ValueError as e:
            return Response({'ok': False, 'errors': {'token': str(e)}}, status=400)

        fields = _clean(request.data, ('name', 'phone', 'company', 'message'))
        errors = {k: 'required' for k in ('name', 'company', 'message') if not fields[k]}
        errors.update(_too_long(fields))
        if errors:
            return Response({'ok': False, 'errors': errors}, status=400)

        config = {'inquiry': {
            'name': fields['name'], 'email': payload['email'], 'phone': fields['phone'],
            'company': fields['company'], 'topic': payload.get('topic', ''), 'page': payload.get('page', ''),
            'email_verified': True, 'token_id': _token_id(token),
        }}
        metadata = {'source': {'type': 'web_inquiry'}}
        classes = schema_classes('action')
        classes['config'].model_validate(config)
        classes['metadata'].model_validate(metadata)

        topic = payload.get('topic') or 'Inquiry'
        action = Action.objects.create(
            status='open',
            kanban_column='Backlog',
            action_type='inquiry',
            priority=2,
            action={'en': f"{topic}: {fields['name']}, {fields['company']}"[:200]},
            description={'en': fields['message']},
            config=config,
            metadata=metadata,
        )
        action.ida = f'INQ-{action.pk}'
        action.save(update_fields=['ida'])
        logger.info('[INQUIRY] action %s from %s', action.ida, payload['email'])
        return Response({'ok': True, 'reference': action.ida})
