"""WCHQ's receiver for records sent by an instance takes only what an instance may set, always
inserts, and receives a record sent twice once (FAULT 2026-11-01: a submitted id overwrote
WCHQ's own row)."""
import json
from types import SimpleNamespace
from unittest import mock

import pytest
from django.test import Client

from apps.core.models import Action
from apps.core.views import instance_submit_view as view

pytestmark = pytest.mark.django_db

SENDER = SimpleNamespace(ida='t-conn-sender', name='Sender', config={'instance_uuid': 't-uuid'})


def _data(r):
    return r.json()['data']              # the response middleware wraps every body


def _submit(record):
    with mock.patch.object(view, 'IS_HQ', True), \
         mock.patch.object(view, '_validate_athena', return_value=(SENDER, None)):
        return Client().post('/wcapi/instance/submit/', json.dumps({'model_name': 'action', 'record': record}),
                             content_type='application/json')


def test_a_submitted_id_does_not_overwrite_hq_rows():
    mine = Action.objects.create(action={'en': 'zz HQ own action'})
    r = _submit({'id': mine.id, 'uuid': str(mine.uuid), 'action': {'en': 'zz from an instance'},
                 'project_id': 999, 'assigned_to': [{'email': 'zz@example.com'}],
                 'refs': {'tags': ['issue'], 'links': {'customer': [{'id': 1}]}}})
    assert r.status_code == 201, r.content
    mine.refresh_from_db()
    assert mine.action == {'en': 'zz HQ own action'}
    sent = Action.objects.get(pk=_data(r)['id'])
    assert sent.pk != mine.pk and sent.uuid != mine.uuid
    assert sent.project_id != 999 and not sent.assigned_to
    assert sent.refs.get('tags') == ['issue'] and 'links' not in (sent.refs or {})
    assert sent.metadata['source_connection']['ida'] == 't-conn-sender'


def test_the_same_record_sent_twice_is_received_once():
    record = {'action': {'en': 'a note'}, 'metadata': {'source_instance': {'local_uuid': 't-local-1'}}}
    first, second = _submit(record), _submit(record)
    assert first.status_code == 201 and second.status_code == 200
    assert _data(second)['duplicate'] is True and _data(second)['id'] == _data(first)['id']


def test_only_hq_receives():
    with mock.patch.object(view, 'IS_HQ', False):
        r = Client().post('/wcapi/instance/submit/', '{}', content_type='application/json')
    assert r.status_code == 404

