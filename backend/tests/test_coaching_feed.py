"""Coaching is each model's help (Bill, 2026-10-28): the model definition holds it, WCHQ's feed
distributes it, feedback is Log rows; QA ids are allocated without holding the counter."""
import pytest

from apps.core.models import Setting
from apps.core.models.log import Log
from tests.conftest import make_setting

pytestmark = pytest.mark.django_db


@pytest.fixture
def invoice_definition():
    Setting.objects.filter(purpose='wc:model', parent_model='invoice').delete()
    return make_setting(purpose='wc:model', parent_model='invoice', name='invoice', config={
        'help': {'tips': [{'id': 'inv-01', 'title': 'Invoices', 'body': 'What you billed.'}],
                 'fields': {'total': 'What the customer owes.'}}})


def test_the_feed_carries_each_models_help(invoice_definition):
    from apps.ai_assistant.services.support_feed import build_coaching_feed
    feed = build_coaching_feed()
    entry = next(e for e in feed['help'] if e['model'] == 'invoice')
    assert entry['help']['fields']['total'] == 'What the customer owes.'


def test_ingest_adds_without_overwriting(invoice_definition):
    from apps.ai_assistant.services.support_feed import ingest_coaching
    result = ingest_coaching({'help': [
        {'model': 'invoice', 'help': {
            'tips': [{'id': 'inv-01', 'title': 'changed upstream'}, {'id': 'inv-02', 'title': 'New'}],
            'fields': {'total': 'upstream text', 'terms': 'When it is due.'}}},
        {'model': 'no_such_model', 'help': {'fields': {'x': 'y'}}},
    ]})
    assert result == {'updated': 1, 'skipped': 1}
    help_ = Setting.objects.get(pk=invoice_definition.pk).config['help']
    assert [t['id'] for t in help_['tips']] == ['inv-01', 'inv-02']
    assert help_['tips'][0]['title'] == 'Invoices'                   # local kept
    assert help_['fields'] == {'total': 'What the customer owes.', 'terms': 'When it is due.'}


def test_feedback_is_log_rows_not_counters(invoice_definition):
    from apps.ai_assistant.services.support_feed import submit_coaching_feedback
    result = submit_coaching_feedback([
        {'model': 'invoice', 'tip_id': 'inv-01', 'rating': 1},
        {'model': 'invoice', 'field': 'total', 'rating': -1, 'comment': 'unclear'},
        {'rating': 1},
    ])
    assert result == {'recorded': 2, 'skipped': 1}
    rows = Log.objects.filter(purpose='alice', action='coaching_feedback', model_name='invoice')
    assert rows.count() == 2
    assert 'feedback' not in Setting.objects.get(pk=invoice_definition.pk).config


def test_qa_ids_are_unique_and_follow_on():
    from apps.docs.services.qa_service import QAService
    service = QAService()
    service.get_or_create_counters()
    first = service.allocate_ids('question', 3)
    second = service.allocate_ids('question', 2)
    assert len(first) == 3 and second == [first[-1] + 1, first[-1] + 2]
    assert service.allocate_ids('answer', 1)[0] >= 1
