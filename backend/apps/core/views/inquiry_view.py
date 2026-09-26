"""Public inquiry → emailed link → form → Action.

1. POST /wcapi/_inquiry/start/  {site, email, topic?, role?, page?, website?}
   Emails a signed link (24 h) to that site's form page (settings.INQUIRY_SITES). Writes nothing.
   The email is plain text, plus HTML when the site's Report has content (editor_type 'html',
   placeholders {{link}}, {{topic}}, {{site_name}}).
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

Limits (Report config.inquiry.limits, InquiryLimits): per visitor IP (Cloudflare's
CF-Connecting-IP) via the throttle rates; link emails per mailbox per UTC day (name+tag@x
counts as name@x) — so nobody can flood someone else's inbox through us; one open inquiry
per Contact per site — a repeat is added to it as a comment. Counters live in the shared
cache (CACHE_URL). A tester mailbox listed in limits.testing skips every limit until its
until_utc (qq — temporary; grep "qq" to remove). Every refusal is logged with its reason.

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
from datetime import datetime, timezone

from django.conf import settings
from django.core import signing
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.mail import EmailMultiAlternatives
from django.utils.html import escape
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


def _site_report(site_key: str):
    """The site's one active form Report, or None — logged, never guessed."""
    rows = list(Report.objects.filter(category='form', is_active=True,
                                      config__inquiry__site=site_key)[:2])
    if len(rows) != 1:
        logger.error('[INQUIRY] site %r: expected one active form Report, found %d', site_key, len(rows))
        return None
    return rows[0]


def _site_form(site_key: str) -> dict:
    """The site's Report config (InquiryForm): who answers, what to ask. {} when there is no
    Report or it does not validate — logged."""
    report = _site_report(site_key)
    if report is None:
        return {}
    try:
        return InquiryForm.model_validate(report.config['inquiry']).model_dump()
    except SchemaError as e:
        logger.error('[INQUIRY] Report %s config.inquiry is invalid: %s', report.pk, e)
        return {}


def _mailbox(email: str) -> str:
    """name+tag@domain → name@domain, lowercased: one mailbox, one count."""
    local, _, domain = (email or '').strip().lower().partition('@')
    return f"{local.split('+', 1)[0]}@{domain}"


# qq — tester exemption (Bill, 2026-09-18, one month). Remove _tester and its callers after testing.
def _tester(form: dict, email: str):
    """The limits.testing entry for this mailbox while its window is open, else None."""
    mailbox = _mailbox(email)
    now = datetime.now(timezone.utc)
    for entry in (form.get('limits') or {}).get('testing') or []:
        if _mailbox(entry['email']) != mailbox:
            continue
        try:
            until = datetime.fromisoformat(entry['until_utc'].replace('Z', '+00:00'))
        except ValueError:
            logger.error('[INQUIRY] tester %s has an unreadable until_utc %r', entry['email'], entry['until_utc'])
            return None
        if now < until:
            return entry
        logger.info('[INQUIRY] tester window for %s ended %s — limits apply', mailbox, entry['until_utc'])
    return None


def _client_ip(request) -> str:
    """The visitor's address: Cloudflare's CF-Connecting-IP (set by Cloudflare on every request
    through the tunnel), else the socket address. Never X-Forwarded-For — the sender writes that."""
    return (request.META.get('HTTP_CF_CONNECTING_IP') or request.META.get('REMOTE_ADDR') or '').strip()


def _refused(reason: str, request, detail: str = ''):
    logger.warning('[INQUIRY] refused %s ip=%s %s', reason, _client_ip(request), detail)


def _link_email_html(site_key: str, values: dict) -> str:
    """The site's Report content with its placeholders filled (values escaped), or ''."""
    report = _site_report(site_key)
    if report is None or report.editor_type != 'html' or not report.content.strip():
        return ''
    html = report.content
    for key, value in values.items():
        html = html.replace('{{' + key + '}}', escape(value))
    return html


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
    tid = _token_id(token)
    if (Action.objects.filter(config__inquiry__token_id=tid).exists()
            or Action.objects.filter(config__inquiry__followup_token_ids__contains=[tid]).exists()):
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


class InquiryThrottle(ScopedRateThrottle):
    """Per visitor IP (CF-Connecting-IP), counted in the shared cache. A tester's own start
    request is not counted."""

    def get_ident(self, request):
        return _client_ip(request)

    def allow_request(self, request, view):
        if request.path.endswith('/start/'):          # qq — tester exemption, remove after testing
            data = getattr(request, 'data', {}) or {}
            email, site = str(data.get('email') or ''), str(data.get('site') or '')
            if email and site in settings.INQUIRY_SITES and _tester(_site_form(site), email):
                return True
        allowed = super().allow_request(request, view)
        if not allowed:
            _refused('ip_rate', request, request.path)
        return allowed


class _Public(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []          # anonymous: no session, so no CSRF coupling
    throttle_classes = [InquiryThrottle]
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

        # Link emails per mailbox per UTC day — nobody floods someone else's inbox through us.
        form = _site_form(fields['site'])
        limit = ((form.get('limits') or {}).get('links_per_mailbox_per_day')) or 3
        if not _tester(form, fields['email']):        # qq — tester exemption, remove after testing
            day = datetime.now(timezone.utc).strftime('%Y%m%d')
            key = 'inq:links:' + hashlib.sha256(f"{_mailbox(fields['email'])}:{day}".encode()).hexdigest()
            cache.add(key, 0, timeout=26 * 3600)
            if cache.incr(key) > limit:
                _refused('mailbox_daily', request, f"limit={limit}")
                return Response({'ok': False, 'errors': {'email': (
                    f'We have already sent {limit} links to this address today — '
                    'please use one of those, or try again tomorrow.')}}, status=429)

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
        html = _link_email_html(fields['site'], {'link': link, 'topic': topic, 'site_name': site['name']})
        try:
            mail = EmailMultiAlternatives(f'Your {topic} form', body, settings.DEFAULT_FROM_EMAIL, [fields['email']])
            if html:
                mail.attach_alternative(html, 'text/html')
            mail.send()
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
                         'questions': ask.get('questions', []), 'note': ask.get('note')})

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
            'email_verified': True, 'token_id': _token_id(token), 'site': payload.get('site', ''),
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
            # One open inquiry per Contact per site: a repeat is added to it, not a new Action.
            one_open = (form.get('limits') or {}).get('one_open_per_contact', True)
            if one_open and not _tester(form, payload['email']):   # qq — tester exemption, remove after testing
                existing = (Action.objects.select_for_update()
                            .filter(action_type='inquiry', status='open',
                                    config__inquiry__contact_id=contact.pk,
                                    config__inquiry__site=payload.get('site', ''))
                            .order_by('-pk').first())
                if existing is not None:
                    return self._add_followup(request, existing, config['inquiry'], token, fields['message'])
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
        logger.info('[INQUIRY] action %s from %s (contact %s%s)', action.ida, payload['email'],
                    contact.pk, ', new' if created else '')
        if not (action.assigned_to and action.assigned_to[0].get('id')):
            # The visitor was promised a person; the Action exists but nobody owns it.
            logger.error('[INQUIRY] %s has no responsible contact — the site %r form Report assign %r '
                         'resolved to no Contact', action.ida, payload.get('site'), form.get('assign'))
        return Response({'ok': True, 'reference': action.ida})

    def _add_followup(self, request, action, inquiry: dict, token: str, message: str):
        """Add a repeat submission to the open inquiry as a comment on the partner channel and
        spend the link. Refused when the channel is full."""
        from common.schemas.envelopes import COMMENT_CHANNEL_MAX_COUNT, COMMENT_TEXT_MAX_LEN
        parts = [f"Again from {inquiry['email']}: {inquiry['name']}, {inquiry['company']} — {message}"]
        if inquiry.get('market_use'):
            parts.append(f"uses the market {inquiry['market_use']}")
        parts += [f"{a['q']} {a['a']}" for a in inquiry.get('answers') or [] if a.get('a')]
        text = ' | '.join(parts)
        from apps.core.services.comment_stamp import append_comment
        # comments.partner, flat, through the one writer — the retired comments.general.foreign
        # was a place no panel read (Fable L5 M-4; Bill: the third channel is 'partner').
        if len((action.comments or {}).get('partner') or []) >= COMMENT_CHANNEL_MAX_COUNT:
            _refused('followups_full', request, action.ida)
            return Response({'ok': False, 'errors': {'message': (
                f'We already have your inquiry ({action.ida}) and several additions — '
                'a person will answer by email.')}}, status=429)
        append_comment(action, 'partner', text[:COMMENT_TEXT_MAX_LEN],
                       source=f"web inquiry: {inquiry['email']}")
        cfg = action.config or {}
        cfg.setdefault('inquiry', {}).setdefault('followup_token_ids', []).append(_token_id(token))
        action.config = cfg
        action.save(update_fields=['comments', 'config'])
        logger.info('[INQUIRY] follow-up added to %s from %s', action.ida, inquiry['email'])
        return Response({'ok': True, 'reference': action.ida, 'followup': True})
