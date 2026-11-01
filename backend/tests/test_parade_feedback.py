"""parade-list and parade-form: each model's app for grouping, and a reviewer's Keep / Modify /
Don't Need on the model kept on its definition (Bill, 2026-11-01)."""
import secrets

import pytest
from rest_framework.test import APIClient

from apps.core.models import Contact, Setting

pytestmark = pytest.mark.django_db


def _client():
    client = APIClient()
    client.force_authenticate(Contact.objects.create_superuser(
        email='zz-parade@example.com', password=secrets.token_urlsafe(16)))
    return client


def test_the_model_list_says_each_models_app():
    r = _client().get('/wcapi/_model_list/', HTTP_HOST='localhost')
    models = {m['name']: m for m in r.json()['data']['models']}
    assert models['item']['app'] == 'products' and models['order']['app'] == 'transactions'
    assert models['order_line']['kind'] == 'line'


def test_feedback_lands_on_the_definition_per_parade():
    client = _client()
    d = Setting.objects.filter(purpose='wc:model', parent_model='item').order_by('id').first()
    for parade, decision in (('list', 'keep'), ('form', 'modify')):
        r = client.post(f'/wcapi/setting/{d.id}/parade_feedback/',
                        {'parade': parade, 'decision': decision, 'notes': 'zz note'}, format='json', HTTP_HOST='localhost')
        assert r.status_code == 200, r.content
    d.refresh_from_db()
    assert d.prefs['parades']['list']['decision'] == 'keep'
    assert d.prefs['parades']['form']['notes'] == 'zz note'
    bad = client.post(f'/wcapi/setting/{d.id}/parade_feedback/', {'parade': 'list', 'decision': 'maybe'},
                      format='json', HTTP_HOST='localhost')
    assert bad.status_code == 400
