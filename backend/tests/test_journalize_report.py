"""The Journalize reports (Bill, 2026-11-07): one per posting model, the unposted records ready
or waiting with the reason; the person ticks and posts, each row through the door
command on its own, with the run's answer per row and a JournalBatch as its audit record."""
import pytest

from apps.core.services.door import Actor
from apps.orgs.models import Customer
from apps.transactions.models import Invoice, InvoiceLine

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin(django_user_model):
    user = django_user_model.objects.create_superuser(
        email='post@example.com', password=None, name_first='Po', name_last='St', username='')
    return Actor(user=user, kind='user', source='command')


@pytest.fixture
def terms():
    from apps.accounts.models import Term
    Term.objects.get_or_create(ida='N30', defaults={'name': 'N30', 'is_active': True})
    return 'N30'


def _invoice(status='released', ida='', terms='N30', lines=1):
    buyer = Customer.objects.create(company='Report Buyer')
    inv = Invoice.objects.create(customer_id=buyer.pk, terms=terms, status=status,
                                 finance={'sales_tax_rate': 0}, totals={'total': 10 * lines})
    if ida:
        Invoice.objects.filter(pk=inv.pk).update(ida=ida)
        inv.refresh_from_db()
    for _ in range(lines):
        InvoiceLine.objects.create(invoice=inv, quantity={'staged': 1, 'active': 1}, price={'unit': 10, 'amount': 10})
    return inv


def test_every_posting_model_has_a_report_record_and_an_executor(chart_of_accounts):
    from apps.core.services.report_registry import EXECUTORS, SHIPPED_REPORTS, seed_shipped_reports
    from apps.core.models.report import Report
    from apps.accounts.services.journalize_report import POSTING_MODELS
    seed_shipped_reports()
    for m in POSTING_MODELS:
        assert f'journalize_{m}' in EXECUTORS
        entry = next(e for e in SHIPPED_REPORTS if e['report_key'] == f'journalize_{m}')
        report = Report.objects.get(ida=f'journalize_{m}')
        assert report.target_model == m and report.output_type == 'screen'
        assert report.config['screen_url'] == entry['screen_url'] == f'/journalize/{m}'


def test_the_report_lists_ready_and_waiting_rows(terms, chart_of_accounts):
    from apps.accounts.services.journalize_report import unposted
    ready = _invoice('released')
    planned = _invoice('planned')
    hollow = _invoice('released', lines=0)
    report = unposted('invoice')
    rows = {r['id']: r for r in report['rows']}
    assert rows[ready.pk]['waiting'] == '' and rows[ready.pk]['preview']['entries']
    # A planned invoice is postable: the post releases it (Bill, 2026-11-08), and the row says so.
    assert rows[planned.pk]['waiting'] == '' and 'releases this planned invoice' in rows[planned.pk]['note']
    assert 'no line' in rows[hollow.pk]['waiting']
    assert report['ready'] == 2 and report['waiting'] == 1 and report['total'] == 3


def test_a_waiting_cash_carries_the_posters_own_words(chart_of_accounts):
    from apps.accounts.services.journalize_report import unposted
    from apps.transactions.models import Cash
    held = Cash.objects.create(amount=25, status='on_hold')
    row = next(r for r in unposted('cash')['rows'] if r['id'] == held.pk)
    assert 'on hold' in row['waiting'].lower()


def test_posting_the_ticked_rows_answers_per_row_and_records_the_run(admin, terms, chart_of_accounts):
    from apps.accounts.models import JournalBatch
    from apps.accounts.services.journalize_report import post_selected
    ready, planned = _invoice('released'), _invoice('planned')
    out = post_selected(admin, 'invoice', [planned.pk, ready.pk, 999999])
    assert [p['id'] for p in out['posted']] == [planned.pk, ready.pk]
    assert {r['id']: r['code'] for r in out['refused']} == {999999: 'not_found'}
    planned_row = next(p for p in out['posted'] if p['id'] == planned.pk)
    assert any('released and posted' in m for m in planned_row['messages'])
    ready.refresh_from_db(); planned.refresh_from_db()
    assert ready.dt_journaled and planned.dt_journaled and planned.status == 'released'
    batch = JournalBatch.objects.get(ida=out['batch'])
    assert batch.batch_type == 'invoice' and batch.count_posted == 2 and batch.count_exceptions == 1
    assert batch.status == JournalBatch.STATUS_HAS_EXCEPTIONS and batch.run_by_id == admin.user.pk
    assert batch.config['refused'][0]['code'] == 'not_found'
    # the posted row has left the report
    from apps.accounts.services.journalize_report import unposted
    assert ready.pk not in {r['id'] for r in unposted('invoice')['rows']}


def test_the_batch_is_gone():
    import apps.accounts.services.journalize as j
    assert not hasattr(j, 'batch_journalize')


# ── nothing of value to post completes; a row's own options; a period (2026-11-27) ──

def _workorder(events=None, line_type='consume'):
    from apps.transactions.models import WorkOrder, WorkOrderLine
    wo = WorkOrder.objects.create(status='active')
    line = WorkOrderLine.objects.create(workorder=wo, line_type=line_type, item={'description': 'part'},
                                        quantity={'active': 1, 'staged': 1})
    if events:          # what a build leaves on its line (a line is not born with events)
        WorkOrderLine.objects.filter(pk=line.pk).update(events=events)
    return wo


def test_a_zero_cash_is_ready_and_posting_completes_it_with_no_gl_entry(admin, chart_of_accounts):
    """FAULT 2026-11-27: posting a zero cash auto-completes it (WC2 rule), but the report showed
    it waiting for good, with no tick box. It is ready now, noted, and posting stamps it."""
    from decimal import Decimal
    from apps.accounts.models import GlJournal
    from apps.accounts.services.journalize_report import COMPLETES_NOTE, post_selected, unposted
    from apps.transactions.models import Cash
    cash = Cash.objects.create(amount=Decimal('0.00'), available=Decimal('0.00'), status='active', method='check')
    row = next(r for r in unposted('cash')['rows'] if r['id'] == cash.pk)
    assert row['waiting'] == '' and row['note'] == COMPLETES_NOTE
    answer = post_selected(admin, 'cash', [cash.pk])
    cash.refresh_from_db()
    assert [p['id'] for p in answer['posted']] == [cash.pk] and cash.dt_journaled
    assert not GlJournal.objects.filter(source_model='cash', source_id=cash.pk).exists()


def test_a_workorder_whose_work_carried_no_value_completes_and_one_with_nothing_done_waits(
        admin, chart_of_accounts):
    """FAULT 2026-11-27 (wc_demo 33, 43-47): the header stayed open for good."""
    from apps.accounts.services.journalize_report import COMPLETES_NOTE, post_selected, unposted
    done = _workorder(events=[{'id': 'e1', 'kind': 'completion', 'qty': 1, 'layer_id': 999999}])
    fresh = _workorder()
    rows = {r['id']: r for r in unposted('workorder')['rows']}
    assert rows[done.pk]['waiting'] == '' and rows[done.pk]['note'] == COMPLETES_NOTE
    assert rows[fresh.pk]['waiting'].startswith('Nothing to journalize')
    post_selected(admin, 'workorder', [done.pk])
    done.refresh_from_db(); fresh.refresh_from_db()
    assert done.dt_journaled and not fresh.dt_journaled


def test_the_options_of_one_row_go_to_that_row_only(admin, terms, chart_of_accounts, monkeypatch):
    """A receipt with unallocated charges posts only with its own post_unallocated tick."""
    from apps.accounts.services import journalize_report
    seen = {}

    def fake(actor, verb, model_key, pk, payload):
        seen[pk] = payload
        return {'created': 1}
    monkeypatch.setattr('apps.core.services.verbs.run_command', fake)
    a, b = _invoice('released'), _invoice('released')
    journalize_report.post_selected(admin, 'invoice', [a.pk, b.pk], {str(b.pk): {'post_unallocated': True}})
    assert seen == {a.pk: {}, b.pk: {'post_unallocated': True}}


def test_the_period_chooses_rows_by_dt_created(terms, chart_of_accounts):
    from apps.accounts.services.journalize_report import unposted
    early, late = _invoice('released'), _invoice('released')
    Invoice.objects.filter(pk=early.pk).update(dt_created=1_790_000_000_000)
    Invoice.objects.filter(pk=late.pk).update(dt_created=1_795_000_000_000)
    ids = lambda **kw: {r['id'] for r in unposted('invoice', **kw)['rows']} & {early.pk, late.pk}  # noqa: E731
    assert ids() == {early.pk, late.pk}
    assert ids(begin=1_791_000_000_000) == {late.pk}
    assert ids(end=1_791_000_000_000) == {early.pk}
    report = unposted('invoice', begin=1_791_000_000_000, end=1_796_000_000_000)
    assert report['begin'] == 1_791_000_000_000 and report['total'] >= 1


def test_the_rows_a_run_posts_name_the_run(admin, terms, chart_of_accounts):
    """A GL row says which run posted it: batch_id is the JournalBatch's ida (2026-11-27)."""
    from apps.accounts.models import GlJournal
    from apps.accounts.services.journalize_report import post_selected
    inv = _invoice('released')
    answer = post_selected(admin, 'invoice', [inv.pk])
    rows = GlJournal.objects.filter(source_model='invoice', source_id=inv.pk)
    assert rows.exists() and set(rows.values_list('batch_id', flat=True)) == {answer['batch']}
