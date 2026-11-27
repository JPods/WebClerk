"""Send a period to accounting: GET /wcapi/reports/gl-export/ for a month (2026-11-27).

The books leave only with accounting, an admin or a superuser (access.ACCOUNTING_ROLES); every staff
role reached it before. A row belongs to its document's period (dt_document, Bill 2026-11-27), not to
the day it posted: a row posted in November for an October document is October's.
"""
import json

import pytest
from rest_framework.test import APIClient

from apps.core.models import Contact

pytestmark = pytest.mark.django_db

URL = '/wcapi/reports/gl-export/'
JSON = 'GL Export — Generic JSON'
OCT_DOC = 1_791_000_000_000          # 2026-10-03, the document's date
NOV_POST = 1_794_500_000_000         # 2026-11-12, the day it posted


def _client(role):
    user = (Contact.objects.filter(email=f'{role}-gl@example.com').first()
            or Contact.objects.create(email=f'{role}-gl@example.com', role=role))
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _row(**kw):
    from apps.accounts.models import GlJournal
    return GlJournal.objects.create(ida='SJ-TEST', account='1100-accounts_receivable', source_model='invoice',
                                    source_id=1, dt_document=OCT_DOC, dt_journaled=NOV_POST, **kw)


@pytest.mark.parametrize('role', ['accounting', 'admin', 'superuser'])
def test_accounting_admin_and_superuser_send_the_books(role):
    response = _client(role).get(URL, {'report': JSON, 'period': '2026-10'})
    assert response.status_code == 200, response.content[:200]


@pytest.mark.parametrize('role', ['sales', 'warehouse', 'support', 'rep', 'production', 'agent'])
def test_other_staff_are_refused(role):
    response = _client(role).get(URL, {'report': JSON, 'period': '2026-10'})
    assert response.status_code == 403 and 'accounting' in str(response.content)


@pytest.mark.usefixtures('chart_of_accounts')
def test_a_row_belongs_to_its_documents_period_not_its_posting_day():
    _row(debit=10.0)
    _row(credit=10.0)
    client = _client('accounting')
    # The JSON-by-default middleware wraps the JSON export in the API envelope: the bundle is its data.
    october = json.loads(client.get(URL, {'report': JSON, 'period': '2026-10'}).content)['data']
    november = json.loads(client.get(URL, {'report': JSON, 'period': '2026-11'}).content)['data']
    assert october['totals'] == {'entry_count': 2, 'total_debits': 10.0, 'total_credits': 10.0, 'balanced': True}
    assert november['totals']['entry_count'] == 0


# ── a list's From/To filters the model's declared period field (config.period_field) ──

def _detail(model_key):
    from apps.core.services import definition
    definition.clear()
    client = _client('superuser')
    response = client.get('/wcapi/_model_detail/', {'model_name': model_key}, HTTP_HOST='localhost')
    assert response.status_code == 200, response.content[:200]
    return response.json()['data']['model']['period_field']


def _definition(model_key, config):
    from apps.core.models import Setting
    from tests.conftest import make_setting
    existing = Setting.objects.filter(purpose='wc:model', parent_model=model_key).first()
    if existing is None:
        return make_setting(purpose='wc:model', parent_model=model_key, name=model_key, config=config)
    existing.config = {**(existing.config or {}), **config}
    existing._setting_create_authorized = True
    existing.save()
    return existing


def test_a_gl_row_is_filtered_by_its_period_and_other_models_by_when_made():
    _definition('gl_journal', {'period_field': 'dt_document'})
    assert _detail('gl_journal') == 'dt_document'
    assert _detail('invoice') == 'dt_created'           # no declaration: when the record was made


@pytest.mark.parametrize('bad', ['dt_nonesuch', 'account', 'debit', ''])
def test_a_period_field_the_model_does_not_have_as_a_date_falls_back(bad):
    _definition('gl_journal', {'period_field': bad})
    assert _detail('gl_journal') == 'dt_created'


def test_the_shipped_bundles_declare_the_gl_rows_period():
    import pathlib
    root = pathlib.Path(__file__).resolve().parents[1]
    for name in ('settings-bundle.json', 'init-bundle.json', 'demo-bundle.json'):
        bundle = json.loads((root / name).read_text())
        gl = next(s for s in bundle['settings'] if s.get('purpose') == 'wc:model' and s.get('parent_model') == 'gl_journal')
        assert gl['config']['period_field'] == 'dt_document', name
