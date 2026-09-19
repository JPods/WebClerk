"""Public inquiry → emailed link → form → Action.

1. POST /wcapi/_inquiry/start/  {site, email, topic?, role?, page?, website?}
   Emails a signed link (24 h) to that site's form page (settings.INQUIRY_SITES). Writes nothing.
2. GET  /wcapi/_inquiry/?t=<token>
   The form page checks its link: {email, topic, role, market_use, questions} or 400
   (expired / tampered / used). market_use and questions come from the site's Report.
3. POST /wcapi/_inquiry/?t=<token>  {name, company, message, phone?, role?, market_use?,
   answers?: [str], website?}
   (the link code rides in the URL, never the body: SecretGuard scans bodies, and the
   visitor's own text should still be scanned)
   Finds the Contact with that email, or creates one (role 'user': no access, no password).
   Creates one Action (action_type='inquiry', Backlog) pointing at it, assigned to the
   Report's `assign` roster; an unresolved answerer is logged as an error. The email comes
   from the token, so it is proven; each token creates at most one Action.

Who answers and what the form asks: the site's Report (category='form',
config.inquiry = common InquiryForm, apps/core/models/action_pydantic.py). No login.
An existing Contact is never overwritten — only its blank name, company and phone are
filled; what the visitor typed is kept on the Action. Accepted fields only, lengths capped, sending mail 5/hour per IP (the form 30/hour),
`website` is a honeypot a person never sees. If mail cannot be sent, the visitor is told —
nothing pretends to have worked. Sites listed in INQUIRY_SITES may call these paths
cross-origin; no other path opens to them.
"""
from __future__ import annotations

import hashlib
import logging

from django.conf import settings
from django.core import signing
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.validators import validate_email
from corsheaders.signals import check_request_enabled
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from django.db import transaction
from pydantic import ValidationError as SchemaError

from apps.core.models import Action, Contact, Report
from apps.core.models.action_pydantic import InquiryForm
from common.schemas.defaults import schema_classes

logger = logging.getLogger(__name__)

SALT = 'wc-inquiry'
MAX_AGE = 24 * 60 * 60
LIMITS = {'site': 40, 'name': 120, 'email': 254, 'phone': 40, 'company': 120, 'role': 60, 'topic': 80,
          'page': 200, 'message': 4000, 'market_use': 60}
ANSWER_LIMIT = 2000


def _site_form(site_key: str) -> dict:
    """The site's Report config (InquiryForm): who answers, what to ask. {} when there is no
    single active Report for the site or it does not validate — logged, never guessed."""
    rows = list(Report.objects.filter(category='form', is_active=True,
                                      config__inquiry__site=site_key)[:2])
    if len(rows) != 1:
        logger.error('[INQUIRY] site %r: expected one active form Report, found %d', site_key, len(rows))
        return {}
    try:
        return InquiryForm.model_validate(rows[0].config['inquiry']).model_dump()
    except SchemaError as e:
        logger.error('[INQUIRY] Report %s config.inquiry is invalid: %s', rows[0].pk, e)
        return {}


def _contact_for(email: str, fields: dict) -> tuple:
    """(contact, created). The email is proven by the link. An existing Contact keeps what it
    has; only blank name, company and phone are filled from the form."""
    from apps.communications.models import Phone
    first, _, last = fields['name'].partition(' ')
    contact = Contact.objects.filter(email__iexact=email).first()
    created = contact is None
    if created:
        contact = Contact.objects.create_user(email=email, name_first=first, name_last=last.strip(),
                                              company=fields['company'], source_name='web inquiry')
    else:
        blanks = {k: v for k, v in (('name_first', first), ('name_last', last.strip()),
                                    ('company', fields['company'])) if v and not getattr(contact, k)}
        if blanks:
            Contact.objects.filter(pk=contact.pk).update(**blanks)
    if fields['phone'] and not contact.phone_id:
        phone = Phone.objects.create(contact_id=contact.pk, number=fields['phone'])
        Contact.objects.filter(pk=contact.pk).update(phone_id=phone.pk)
    return contact, created


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


def _inquiry_cors(sender, request, **kwargs):
    if not request.path.startswith('/wcapi/_inquiry/'):
        return False
    origin = request.headers.get('Origin', '')
    return any(origin in site['origins'] for site in settings.INQUIRY_SITES.values())


check_request_enabled.connect(_inquiry_cors, dispatch_uid='wc-inquiry-cors')


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
        fields = _clean(request.data, ('site', 'email', 'topic', 'role', 'page'))
        errors = _too_long(fields)
        site = settings.INQUIRY_SITES.get(fields['site'])
        if site is None:
            errors['site'] = f"unknown site — expected one of {', '.join(settings.INQUIRY_SITES)}"
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
        link = request.build_absolute_uri(f"{site['form_url']}?t={token}")
        topic = fields['topic'] or site['name']
        body = (
            f"Thank you for your interest in {topic}.\n\n"
            f"Open this link to tell us who you are and what you need. It works once, for 24 hours:\n\n"
            f"{link}\n\n"
            f"If you did not ask for this, ignore this email — nothing has been recorded.\n\n"
            f"{site['name']}\n"
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
        ask = _site_form(payload.get('site', '')).get('ask', {})
        return Response({'ok': True, 'email': payload['email'], 'topic': payload.get('topic', ''),
                         'role': payload.get('role', ''), 'market_use': ask.get('market_use', []),
                         'questions': ask.get('questions', [])})

    def post(self, request):
        if str(request.data.get('website') or '').strip():
            return Response({'ok': True})
        token = str(request.query_params.get('t') or '')
        try:
            payload = _read_token(token)
        except ValueError as e:
            return Response({'ok': False, 'errors': {'token': str(e)}}, status=400)

        form = _site_form(payload.get('site', ''))
        ask = form.get('ask', {})
        fields = _clean(request.data, ('name', 'phone', 'company', 'role', 'message', 'market_use'))
        errors = {k: 'required' for k in ('name', 'company', 'message') if not fields[k]}
        errors.update(_too_long(fields))
        if ask.get('market_use') and fields['market_use'] not in ask['market_use']:
            errors['market_use'] = 'choose one: ' + ', '.join(ask['market_use'])
        raw = request.data.get('answers') or []
        questions = ask.get('questions', [])
        if not isinstance(raw, list) or len(raw) > len(questions):
            errors['answers'] = f'at most {len(questions)} answers'
            raw = []
        answers = [str(a or '').strip() for a in raw] + [''] * (len(questions) - len(raw))
        if any(len(a) > ANSWER_LIMIT for a in answers):
            errors['answers'] = f'each answer at most {ANSWER_LIMIT} characters'
        if errors:
            return Response({'ok': False, 'errors': errors}, status=400)

        config = {'inquiry': {
            'name': fields['name'], 'email': payload['email'], 'phone': fields['phone'],
            'company': fields['company'], 'role': fields['role'] or payload.get('role', ''),
            'topic': payload.get('topic', ''), 'page': payload.get('page', ''),
            'email_verified': True, 'token_id': _token_id(token),
            'market_use': fields['market_use'],
            'answers': [{'q': q, 'a': a} for q, a in zip(questions, answers)],
        }}
        metadata = {'source': {'type': 'web_inquiry'}}
        classes = schema_classes('action')
        classes['config'].model_validate(config)
        classes['metadata'].model_validate(metadata)

        topic = payload.get('topic') or 'Inquiry'
        with transaction.atomic():
            contact, created = _contact_for(payload['email'], fields)
            config['inquiry'].update(contact_id=contact.pk, contact_created=created)
            classes['config'].model_validate(config)
            action = Action.objects.create(
                status='open',
                kanban_column='Backlog',
                action_type='inquiry',
                priority=2,
                action={'en': f"{topic}: {fields['name']}, {fields['company']}"[:200]},
                description={'en': fields['message']},
                assigned_to=[dict(p) for p in form.get('assign', [])],
                config=config,
                metadata=metadata,
            )
            action.ida = f'INQ-{action.pk}'
            action.save(update_fields=['ida'])
        logger.info('[INQUIRY] action %s from %s (contact %s%s)', action.ida, payload['email'],
                    contact.pk, ', new' if created else '')
        if not (action.assigned_to and action.assigned_to[0].get('id')):
            # The visitor was promised a person; the Action exists but nobody owns it.
            logger.error('[INQUIRY] %s has no responsible contact — the site %r form Report assign %r '
                         'resolved to no Contact', action.ida, payload.get('site'), form.get('assign'))
        return Response({'ok': True, 'reference': action.ida})
