"""Every call to Claude goes through one door: a Connection for the key and a Bundle for the
record, written before anything is sent (Bill, 2026-11-22)."""
import re
import secrets
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import httpx
import pytest

from apps.sync.models import Bundle, Connection
from apps.sync.services import claude_api
from apps.sync.services.connections import ConnectionUnavailable, set_credentials

BACKEND = Path(claude_api.__file__).resolve().parents[3]
# A fresh random stand-in each run: no key, real or fake, is written in this file.
TEST_KEY = secrets.token_hex(12)


def _connection(model=''):
    conn = Connection(name='Claude', status='active', is_active=True,
                      config={'channel': 'claude_api', 'provider': 'anthropic', 'model': model})
    set_credentials(conn, {'api_key': TEST_KEY})
    conn.save()
    return conn


def _reply(text='mapped', stop_reason='end_turn', model='claude-sonnet-5-5'):
    return {'content': [{'type': 'thinking', 'thinking': ''}, {'type': 'text', 'text': text}],
            'usage': {'input_tokens': 11, 'output_tokens': 7}, 'stop_reason': stop_reason,
            'model': model}


def _http(status=200, body=None, headers=None):
    return SimpleNamespace(status_code=status, json=lambda: body if body is not None else _reply(),
                           text=str(body), headers=headers or {})


@pytest.fixture
def sdk():
    """Stands in for Anthropic's HTTPS endpoint; records what it was sent. `answers` is the
    queue of responses (or exceptions) to give, the last one repeating."""
    seen = {'answers': [], 'posts': 0}

    def post(url, headers, json, timeout):
        seen.update(url=url, headers=headers, request=json)
        seen['api_key'] = headers['x-api-key']
        seen['bundles_when_sent'] = list(Bundle.objects.values_list('status', flat=True))
        seen['posts'] += 1
        answers = seen['answers']
        answer = (answers.pop(0) if len(answers) > 1 else answers[0]) if answers else _http()
        if isinstance(answer, Exception):
            raise answer
        return answer

    with mock.patch.object(claude_api.httpx, 'post', side_effect=post), \
         mock.patch.object(claude_api.time, 'sleep'):
        yield seen


MESSAGES = [{'role': 'user', 'content': 'Map these columns.'}]


@pytest.mark.django_db
def test_a_call_uses_the_connection_key_and_leaves_a_bundle(sdk):
    conn = _connection()
    reply = claude_api.ask(purpose='conversion_column_map', messages=MESSAGES, system='Be brief.',
                           max_tokens=500)
    assert (reply.text, reply.usage, reply.model) == (
        'mapped', {'input_tokens': 11, 'output_tokens': 7}, 'claude-sonnet-5-5')
    assert sdk['api_key'] == TEST_KEY
    assert sdk['url'] == 'https://api.anthropic.com/v1/messages'
    assert sdk['headers']['anthropic-version'] == '2026-10-21'
    assert sdk['request'] == {'model': 'claude-sonnet-5-5', 'max_tokens': 500,
                              'messages': MESSAGES, 'system': 'Be brief.'}

    bundle = Bundle.objects.get(pk=reply.bundle_id)
    assert (bundle.connection_id, bundle.direction, bundle.status) == (conn.pk, 'push', 'success')
    assert bundle.config['purpose'] == 'conversion_column_map'
    assert bundle.response == {'text': 'mapped', 'stop_reason': 'end_turn',
                               'usage': {'input_tokens': 11, 'output_tokens': 7},
                               'model': 'claude-sonnet-5-5', 'attempts': 1}
    assert bundle.get_payload() == sdk['request']          # exactly what left the box
    assert '/complete/' in bundle.config['payload_path']
    assert bundle.dt_processed > 0
    assert TEST_KEY not in str(bundle.config) + str(bundle.response) + str(bundle.get_payload())


@pytest.mark.django_db
def test_the_bundle_exists_before_anything_is_sent(sdk):
    _connection()
    claude_api.ask(purpose='alice_escalation', messages=MESSAGES)
    assert sdk['bundles_when_sent'] == ['running']


@pytest.mark.django_db
def test_no_bundle_no_call(sdk):
    _connection()
    with mock.patch.object(Bundle.objects, 'create', side_effect=RuntimeError('disk full')):
        with pytest.raises(RuntimeError, match='disk full'):
            claude_api.ask(purpose='alice_escalation', messages=MESSAGES)
    assert 'request' not in sdk


@pytest.mark.django_db
def test_the_model_comes_from_the_connection_unless_named(sdk):
    _connection(model='claude-haiku-5-5')
    claude_api.ask(purpose='p', messages=MESSAGES)
    assert sdk['request']['model'] == 'claude-haiku-5-5'
    claude_api.ask(purpose='p', messages=MESSAGES, model='claude-opus-5-5')
    assert sdk['request']['model'] == 'claude-opus-5-5'


@pytest.mark.django_db
def test_no_connection_is_a_refusal_and_sends_nothing(sdk):
    with pytest.raises(ConnectionUnavailable):
        claude_api.ask(purpose='p', messages=MESSAGES)
    assert 'request' not in sdk and Bundle.objects.count() == 0


@pytest.mark.django_db
def test_a_revoked_connection_stops_the_call(sdk):
    conn = _connection()
    conn.status = 'inactive'
    conn.save()
    with pytest.raises(ConnectionUnavailable):
        claude_api.ask(purpose='p', messages=MESSAGES)
    assert 'request' not in sdk


@pytest.mark.django_db
def test_a_connection_without_a_key_is_refused(sdk):
    conn = _connection()
    set_credentials(conn, {'api_key': ''})
    conn.save()
    with pytest.raises(ValueError, match='no credentials.api_key'):
        claude_api.ask(purpose='p', messages=MESSAGES)
    assert 'request' not in sdk


@pytest.mark.django_db
def test_a_purpose_is_required(sdk):
    _connection()
    with pytest.raises(ValueError, match='needs a purpose'):
        claude_api.ask(purpose='', messages=MESSAGES)
    assert 'request' not in sdk


@pytest.mark.django_db
def test_an_api_error_is_recorded_and_raised(sdk):
    _connection()
    sdk['answers'] = [_http(400, {'type': 'error', 'request_id': 'req_1',
                                  'error': {'type': 'invalid_request_error', 'message': 'bad model'}})]
    with pytest.raises(claude_api.ClaudeError, match='400: bad model') as e:
        claude_api.ask(purpose='p', messages=MESSAGES)
    assert (e.value.status_code, e.value.error_type, sdk['posts']) == (400, 'invalid_request_error', 1)
    bundle = Bundle.objects.get()
    assert bundle.status == 'error'
    assert bundle.response == {'error': 'invalid_request_error', 'status_code': 400,
                               'request_id': 'req_1', 'message': 'Claude API error 400: bad model'}
    assert '/defects/' in bundle.config['payload_path']
    assert bundle.get_payload()['messages'] == MESSAGES


@pytest.mark.django_db
def test_overload_is_retried_then_succeeds(sdk):
    _connection()
    sdk['answers'] = [_http(529, {'type': 'error', 'error': {'type': 'overloaded_error', 'message': 'busy'}}),
                      httpx.ConnectError('reset'), _http()]
    reply = claude_api.ask(purpose='p', messages=MESSAGES)
    assert (reply.text, sdk['posts']) == ('mapped', 3)
    assert Bundle.objects.get().response['attempts'] == 3


@pytest.mark.django_db
def test_three_failures_stop_and_are_recorded(sdk):
    _connection()
    sdk['answers'] = [httpx.ConnectTimeout('no route')]
    with pytest.raises(claude_api.ClaudeError, match='did not answer after 3 attempts'):
        claude_api.ask(purpose='p', messages=MESSAGES)
    assert sdk['posts'] == 3
    assert Bundle.objects.get().status == 'error'


@pytest.mark.django_db
def test_a_refusal_is_recorded_and_raised(sdk):
    _connection()
    sdk['answers'] = [_http(body=_reply(text='', stop_reason='refusal'))]
    with pytest.raises(claude_api.ClaudeRefused, match='declined'):
        claude_api.ask(purpose='p', messages=MESSAGES)
    bundle = Bundle.objects.get()
    assert (bundle.status, bundle.response['stop_reason']) == ('warning', 'refusal')


@pytest.mark.django_db
def test_escalation_goes_through_the_door(sdk):
    from apps.ai_assistant.services.escalation import ask_claude
    _connection()
    sdk['answers'] = [_http(body=_reply(text='Use price level 3.'))]
    answer, usage, model = ask_claude('Which tier?', 'not sure', '', 'ctx', 'general')
    assert (answer, usage['output_tokens'], model) == ('Use price level 3.', 7, 'claude-sonnet-5-5')
    assert Bundle.objects.get().config['purpose'] == 'alice_escalation'
    assert 'Question: Which tier?' in sdk['request']['messages'][0]['content']


@pytest.mark.django_db
def test_escalation_without_a_connection_says_so(sdk):
    from apps.ai_assistant.services.escalation import ask_claude
    with pytest.raises(ValueError, match='No Claude API Connection'):
        ask_claude('q', '', '', '', 'general')


@pytest.mark.django_db
def test_the_converter_scrubs_its_sample_and_goes_through_the_door(sdk):
    from apps.conversion.services import converter
    _connection()
    sdk['answers'] = [_http(body=_reply(text='[]'))]
    source = SimpleNamespace(
        raw_headers=['sku', 'contact'], filename='parts.csv',
        sample_rows=[{'sku': 'AB-100', 'contact': 'pat@example.com'}])
    log = SimpleNamespace(llm_calls=0, llm_input_tokens=0, llm_output_tokens=0,
                          duration_seconds=0.0, llm_model='')
    assert converter.run_column_mapping(source, log) == []
    prompt = sdk['request']['messages'][0]['content']
    assert 'AB-100' in prompt and 'pat@example.com' not in prompt
    assert (log.llm_calls, log.llm_input_tokens, log.llm_model) == (1, 11, 'claude-sonnet-5-5')
    bundle = Bundle.objects.get()
    assert bundle.config['purpose'] == 'conversion_column_map'
    assert 'pat@example.com' not in str(bundle.get_payload())


def test_only_the_door_calls_anthropic_and_no_sdk_is_imported():
    offenders = []
    for path in (BACKEND / 'apps').rglob('*.py'):
        if '/tests/' in str(path):
            continue
        text = path.read_text(errors='ignore')
        door = path == Path(claude_api.__file__).resolve()
        if re.search(r'^\s*(import|from)\s+anthropic\b', text, re.M) or (
                'api.anthropic.com' in text and not door):
            offenders.append(str(path.relative_to(BACKEND)))
    assert offenders == []
    assert 'anthropic' not in (BACKEND / 'requirements.txt').read_text().lower()
