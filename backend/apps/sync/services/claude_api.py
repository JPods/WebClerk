"""The one door to Claude (Bill, 2026-11-22: every outside call goes through a Connection and
a Bundle).

- The key and the default model come from this server's one active Connection with channel
  'claude_api'. No Connection, no call; revoke the Connection and every call stops.
- A Bundle is written BEFORE anything is sent, holding exactly what will leave the box. If
  the Bundle cannot be written, nothing is sent. The reply, token counts and duration are
  added when the call returns; a failure is recorded on the same Bundle and raised.

The call is one HTTPS POST made with httpx: no vendor SDK is installed. Nothing else in the
code base may call Anthropic's API or import its SDK (tests/test_claude_door.py holds that).
"""
import logging
import time
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

CHANNEL = 'claude_api'
DEFAULT_MODEL = 'claude-sonnet-5-5'
API_URL = 'https://api.anthropic.com/v1/messages'
API_VERSION = '2026-10-21'
TIMEOUT = 300                 # seconds for one attempt
RETRY_STATUSES = frozenset({429, 500, 502, 503, 504, 529})
RETRY_WAITS = (1.0, 3.0)      # seconds before the second and third attempts
BUNDLE_MODEL_NAME = 'claude_api'      # not a record model: files land in bundles/general/


@dataclass(frozen=True)
class ClaudeReply:
    text: str
    usage: dict
    model: str
    stop_reason: str
    bundle_id: int


class ClaudeRefused(RuntimeError):
    """Claude declined the request (stop_reason 'refusal'). The Bundle holds the detail."""


class ClaudeError(RuntimeError):
    """The API answered with an error, or did not answer. The Bundle holds the detail."""

    def __init__(self, message: str, status_code: int = 0, error_type: str = '', request_id: str = ''):
        super().__init__(message)
        self.status_code, self.error_type, self.request_id = status_code, error_type, request_id


def _post(api_key: str, body: dict) -> tuple[dict, int]:
    """One request, retried on overload and server errors. Returns (reply, attempts)."""
    headers = {'x-api-key': api_key, 'anthropic-version': API_VERSION,
               'content-type': 'application/json'}
    attempts = 0
    while True:
        attempts += 1
        retry = attempts <= len(RETRY_WAITS)
        try:
            r = httpx.post(API_URL, headers=headers, json=body, timeout=TIMEOUT)
        except httpx.HTTPError as e:
            if retry:
                time.sleep(RETRY_WAITS[attempts - 1])
                continue
            raise ClaudeError(f"Claude did not answer after {attempts} attempts: {e}") from e
        if r.status_code == 200:
            return r.json(), attempts
        if r.status_code in RETRY_STATUSES and retry:
            try:
                wait = float(r.headers.get('retry-after', ''))
            except ValueError:
                wait = RETRY_WAITS[attempts - 1]
            time.sleep(min(wait, 30.0))
            continue
        try:
            detail = r.json()
        except ValueError:
            detail = {}
        err = detail.get('error') or {}
        raise ClaudeError(
            f"Claude API error {r.status_code}: {err.get('message') or r.text[:300]}",
            status_code=r.status_code, error_type=err.get('type', ''),
            request_id=detail.get('request_id', ''))


def ask(*, purpose: str, messages: list[dict], system: str = '', max_tokens: int = 2048,
        model: str = '') -> ClaudeReply:
    """Send one request to Claude through the Connection, recorded as a Bundle.

    purpose: a short name for why this is sent ('alice_escalation', 'conversion_column_map').
    model: '' uses the Connection's config.model, else DEFAULT_MODEL.

    Raises ConnectionUnavailable (no single active Connection), ValueError (the Connection
    has no key), ClaudeRefused, or ClaudeError after recording it.
    """
    from apps.sync.models import Bundle
    from apps.sync.services import bundle_storage
    from apps.sync.services.connections import active_connection, credentials

    if not purpose:
        raise ValueError("ask() needs a purpose: the Bundle must say why this left the box")
    conn = active_connection(CHANNEL)
    api_key = credentials(conn).get('api_key', '')
    if not api_key:
        raise ValueError(f"Connection {conn.pk} ({conn.name}) has no credentials.api_key")
    model = model or (conn.config or {}).get('model') or DEFAULT_MODEL

    sent = {'model': model, 'max_tokens': max_tokens, 'messages': messages}
    if system:
        sent['system'] = system

    # The record comes first. If this fails, nothing is sent.
    bundle = Bundle.objects.create(
        connection=conn, direction='push', model_name=BUNDLE_MODEL_NAME, status='running',
        config={'channel': CHANNEL, 'purpose': purpose, 'model': model, 'max_tokens': max_tokens},
        size=len(str(sent)),
    )
    bundle.save_payload_to_disk(sent)

    def close(status: str, response: dict, folder: str, started: float) -> None:
        bundle.status = status
        bundle.response = response
        bundle.duration = int((time.time() - started) * 1000)
        bundle.dt_processed = int(time.time() * 1000)
        bundle.size += len(str(response))
        path = bundle_storage.move(bundle.pk, BUNDLE_MODEL_NAME, 'push', folder)
        if path:
            bundle.config = {**bundle.config, 'payload_path': path}
        bundle.save()

    started = time.time()
    try:
        reply, attempts = _post(api_key, sent)
    except ClaudeError as e:
        close('error', {'error': e.error_type or type(e).__name__, 'message': str(e)[:1000],
                        'status_code': e.status_code, 'request_id': e.request_id},
              'defects', started)
        raise

    used = reply.get('usage') or {}
    usage = {'input_tokens': used.get('input_tokens', 0), 'output_tokens': used.get('output_tokens', 0)}
    stop_reason = reply.get('stop_reason') or ''
    answered_by = reply.get('model', model)
    if stop_reason == 'refusal':
        close('warning', {'stop_reason': stop_reason, 'stop_details': reply.get('stop_details'),
                          'usage': usage, 'model': answered_by, 'attempts': attempts},
              'defects', started)
        raise ClaudeRefused(f"Claude declined this request (purpose {purpose}); Bundle {bundle.pk}")

    text = ''.join(block.get('text', '') for block in reply.get('content') or []
                   if block.get('type') == 'text')
    close('success', {'text': text, 'stop_reason': stop_reason, 'usage': usage,
                      'model': answered_by, 'attempts': attempts}, 'complete', started)
    return ClaudeReply(text=text, usage=usage, model=answered_by, stop_reason=stop_reason,
                       bundle_id=bundle.pk)
