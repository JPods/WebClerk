"""Import plan §17.5 security gaps (Bill, 2026-09-27): the shared bundle key never leaves the server;
receiving a bundle imports nothing; the dev tools need a signed-in superuser."""
import json

import pytest

from apps.sync.models import Bundle, Connection

pytestmark = pytest.mark.django_db


def _conn(key='k-' + 'x' * 30, **kw):
    conn = Connection.objects.create(name='Partner', type='api', status='active', **kw)
    conn.set_sync_key(key)
    conn.save()
    return conn


def test_the_record_api_never_returns_the_key(client, django_user_model):
    conn = _conn(config={'endpoint': 'https://partner.example/wcapi/sync/receive/'})
    boss = django_user_model.objects.create_user(email='boss@wc.test', password='x', username='',
                                                 is_superuser=True, role='admin')
    client.force_login(boss)
    body = client.get(f'/wcapi/connection/{conn.pk}/').content.decode()
    assert 'k-xxxx' not in body and 'sync_key' not in body


def test_the_receiver_takes_the_key_from_encryption_and_imports_nothing(client):
    conn = _conn()
    r = client.post('/wcapi/sync/receive/', {'payload': {'model_name': 'item', 'records': []}},
                    content_type='application/json', HTTP_X_SYNC_KEY='k-' + 'x' * 30)
    body = r.json().get('data') or r.json()             # the API envelope wraps the ack
    assert r.status_code == 200 and body['ack'] is True
    bundle = Bundle.objects.get(pk=int(body['bundle_id']))
    assert bundle.connection_id == conn.pk and bundle.status == '', 'received, not "success"'


def test_a_key_left_in_config_opens_nothing(client):
    Connection.objects.create(name='Old', type='api', status='active', config={'key': 'old-key'})
    r = client.post('/wcapi/sync/receive/', {}, content_type='application/json', HTTP_X_SYNC_KEY='old-key')
    assert r.status_code == 403


def test_the_migration_moves_keys_and_drops_the_literal_self_key():
    import importlib
    from django.apps import apps
    move_keys = importlib.import_module('apps.sync.migrations.0009_sync_key_to_encryption').move_keys
    real = Connection.objects.create(name='Real', type='api', config={'key': 'real-key', 'endpoint': 'e'})
    self_conn = Connection.objects.create(name='Self', type='internal', config={'key': 'self-connection'})
    move_keys(apps, None)
    real.refresh_from_db(); self_conn.refresh_from_db()
    assert 'key' not in real.config and real.sync_key == 'real-key' and real.config['endpoint'] == 'e'
    assert 'key' not in self_conn.config and self_conn.sync_key == ''


def test_the_self_connection_gets_a_random_key():
    from django.core.management import call_command
    call_command('seed_self_connection')
    conn = Connection.objects.get(ida='self-connection')
    assert len(conn.sync_key) >= 32 and conn.sync_key != 'self-connection'


@pytest.mark.parametrize('path', ['/wcapi/_dev_sync/', '/wcapi/_dev_switch/', '/wcapi/_dev_restart/'])
def test_the_dev_tools_need_a_superuser(client, django_user_model, path):
    from django.urls import resolve
    resolve(path)                                         # routed, or the test is wrong
    r = client.post(path, json.dumps({'direction': 'upload'}), content_type='application/json')
    assert r.status_code == 403 and 'superuser' in json.dumps(r.json())
    clerk = django_user_model.objects.create_user(email='clerk@wc.test', password='x', username='', role='admin')
    client.force_login(clerk)
    r = client.post(path, json.dumps({'direction': 'upload'}), content_type='application/json')
    assert r.status_code == 403 and 'superuser' in json.dumps(r.json())
