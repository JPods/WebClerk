"""One source of truth for calculations (readme 111; Bill, 2026-11-12).

"Browser is a preview so users do not have to wait for server, but the source of truth is the
server." Rulings: commission is computed by the server at save; one function owns a document's
balance; rounding is "up if half or more, down if less than half" everywhere; the second tax
calculator is gone.
"""
import threading
from decimal import Decimal
from types import SimpleNamespace

import pytest

from apps.core.services.door import Actor
from apps.core.services.save import save_record
from apps.orgs.models import OrgBase
from apps.transactions.models import Invoice, InvoiceLine
from apps.transactions.services.pricing import commission_compute
from apps.transactions.services.pricing.totals_compute import balance_of
from common.decimals import money

CENT = Decimal('0.01')


# ── Rounding ────────────────────────────────────────────────────────────────

def test_a_bare_quantize_rounds_half_up():
    assert Decimal('0.125').quantize(CENT) == Decimal('0.13')
    assert Decimal('0.135').quantize(CENT) == Decimal('0.14')
    assert Decimal('0.124').quantize(CENT) == Decimal('0.12')
    assert Decimal('-0.125').quantize(CENT) == Decimal('-0.13')


def test_a_new_thread_rounds_half_up_too():
    seen = []
    worker = threading.Thread(target=lambda: seen.append(Decimal('2.665').quantize(CENT)))
    worker.start()
    worker.join()
    assert seen == [Decimal('2.67')]


def test_money_is_cents_half_up():
    assert money('8.575') == Decimal('8.58')
    assert money(None) == Decimal('0.00')


def test_percent_of_goods_shipping_rounds_half_up(monkeypatch):
    from apps.transactions.services.fulfillment import fulfillment_freight
    monkeypatch.setattr(fulfillment_freight, 'shipping_service_for',
                        lambda ship_via: {'rate_method': 'percent_of_goods', 'rate_percent': 2.5})
    assert fulfillment_freight.percent_of_goods_shipping('ups', Decimal('1.00')) == Decimal('0.03')


# ── Balance ─────────────────────────────────────────────────────────────────

def test_balance_is_total_less_settled_less_adjusted():
    assert balance_of(100, 60, 40) == Decimal('0.00')
    assert balance_of('100.00', None, None) == Decimal('100.00')
    assert balance_of(10, 10.005) == Decimal('-0.01')


def test_a_payable_written_off_in_part_is_paid(monkeypatch):
    """cash_door left `adjusted` out, so 60 paid and 40 written off read 'partially_paid'."""
    from apps.transactions.services.cash import cash_door, cash_pending_receipt
    monkeypatch.setattr(cash_pending_receipt, '_applied', lambda receipt_id: Decimal('60.00'))
    saved = []
    receipt = SimpleNamespace(pk=1, status='open', totals={'total': 100.0, 'adjusted': 40.0},
                              save=lambda **kw: saved.append(kw))
    cash_door._refresh_receipt_status(receipt)
    assert receipt.status == 'paid' and saved

    receipt = SimpleNamespace(pk=1, status='open', totals={'total': 100.0},
                              save=lambda **kw: saved.append(kw))
    cash_door._refresh_receipt_status(receipt)
    assert receipt.status == 'partially_paid'


# ── Commission ──────────────────────────────────────────────────────────────

def test_the_one_formula_rounds_half_up():
    # 8.50 × 5% = 0.425 → 0.43 (float round gave 0.42)
    assert commission_compute.rep_amount(Decimal('8.50'), 5) == Decimal('0.43')
    assert commission_compute.rep_amount(100, 10, 0.7, 50) == Decimal('3.50')
    assert commission_compute.effective_rate(10, 0.7, 50) == 3.5


def test_populate_and_settle_agree():
    made = commission_compute.calculate_line_commission(
        100.0, 60.0, 'wholesale', [{'rep_id': 7, 'rate_pct': 10, 'split_pct': 50, 'basis': 'margin'}])
    settled = commission_compute.settle_line_commission(
        {**made, 'reps': [{**made['reps'][0], 'amount': 999}]}, {'amount': 100.0, 'cost': 60.0})
    assert made['reps'][0]['amount'] == settled['reps'][0]['amount'] == 1.4
    assert made['total'] == settled['total'] == 1.4


def test_an_accrued_commission_is_left_alone():
    assert commission_compute.settle_line_commission(
        {'accrued': True, 'reps': [{'rep_id': 1, 'rate_pct': 5, 'amount': 3}]}, {'amount': 100}) is None
    assert commission_compute.sum_header_commission({'accrued': True}, [{'reps': [{'rep_id': 1, 'amount': 3}]}]) is None


def test_a_document_commission_with_no_line_reps_is_left_alone():
    assert commission_compute.sum_header_commission({'reps': [{'rep_id': 1, 'amount': 12}], 'total': 12},
                                                    [{}, None, {'reps': []}]) is None


@pytest.fixture(autouse=True)
def _no_pending_dispatch(monkeypatch):
    monkeypatch.setattr("apps.products.dispatch_pending.dispatch_pending_processing",
                        lambda *args, **kwargs: None)


@pytest.fixture
def admin(django_user_model):
    return django_user_model.objects.create_superuser(
        email='onesource@example.com', password=None, name_first='One', name_last='Source', username='')


@pytest.mark.django_db
def test_the_save_stores_the_servers_commission_not_the_browsers(admin, model_defaults):
    """The browser sends the amount it showed; what is stored is the server's figure, and the
    document's commission is the sum of its lines'."""
    store = OrgBase.objects.create(company='Commission Customer', org_type='customer')
    inv = Invoice.objects.create(status='planned', customer_id=store.id, finance={'sales_tax_rate': 0})
    a = InvoiceLine.objects.create(invoice=inv, item={'description': 'A'}, price={'unit': 8.50, 'precision': 2},
                                   quantity={'active': 1, 'precision': 2})
    b = InvoiceLine.objects.create(invoice=inv, item={'description': 'B'}, price={'unit': 200.0, 'precision': 2},
                                   quantity={'active': 1, 'precision': 2})
    inv.refresh_from_db(); a.refresh_from_db(); b.refresh_from_db()

    def sent(rate, wrong):
        return {'reps': [{'rep_id': 7, 'name': 'Rep Seven', 'rate_pct': rate, 'level_factor': 1.0,
                          'split_pct': 100, 'amount': wrong, 'effective_rate': 99, 'override': True}],
                'total': wrong, 'basis': 'revenue'}

    save_record(Actor(user=admin, kind='user', source='wcapi'), {
        'id': inv.pk, 'version': inv.version, 'lines': [
            {'id': a.pk, 'version': a.version, '_dirty': True, 'commission': sent(5, 0.42)},
            {'id': b.pk, 'version': b.version, '_dirty': True, 'commission': sent(10, 1234.56)}]},
        model_key='invoice')
    a.refresh_from_db(); b.refresh_from_db(); inv.refresh_from_db()

    assert a.commission['reps'][0]['amount'] == 0.43          # 8.50 × 5%, half-up
    assert a.commission['reps'][0]['effective_rate'] == 5.0
    assert a.commission['total'] == 0.43
    assert b.commission['reps'][0]['amount'] == 20.0
    assert b.commission['total'] == 20.0
    assert inv.commission['total'] == 20.43
    assert [(r['rep_id'], r['amount']) for r in inv.commission['reps']] == [(7, 20.43)]


# ── One tax calculator ──────────────────────────────────────────────────────

def test_the_second_tax_calculator_is_gone():
    from apps.accounts.services import tax_calculation
    from apps.core.views.manage_view import _ACTION_DISPATCH
    assert not hasattr(tax_calculation, 'calculate_line_tax')
    assert 'calculate_line_tax' not in _ACTION_DISPATCH
    assert 'get_tax_jurisdictions' in _ACTION_DISPATCH
