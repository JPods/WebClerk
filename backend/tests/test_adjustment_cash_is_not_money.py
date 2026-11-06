"""A discount, write-off, small-balance or FX Cash is an adjustment, never money (plan 102,
Bill 2026-11-02: each adjustment is its own Cash record with its own GL). period_close already
leaves them out of cash received; the cash card, the commerce dashboard and the bank side must
too: an adjustment never reaches a bank statement, so it is never reconciled and no statement
line names it."""
from decimal import Decimal

import pytest

from apps.core.services.dashboard.dd_card_metrics import card_metrics
from apps.core.services.door import Actor, Refused
from apps.core.services.save import save_record
from apps.transactions.models import Cash
from apps.transactions.services.cash.cash_pending import ADJUSTMENT_METHODS

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin(django_user_model):
    return Actor(user=django_user_model.objects.create_superuser(
        email='adj@example.com', password=None, name_first='Ad', name_last='Just', username=''), kind='user')


def _cash(amount, method='check', **kw):
    return Cash.objects.create(amount=Decimal(str(amount)), available=Decimal(str(amount)), method=method,
                               status='complete', **kw)


def _money_and_adjustments():
    _cash(100, 'check'); _cash(50, 'card'); _cash(-20, 'check')   # money in, in, out
    for method in ADJUSTMENT_METHODS:
        _cash(2, method)                                           # five adjustments, 2 each


def test_the_cash_card_counts_money_only(admin):
    """The seeded cash card (seed_dd_cards): Received and Disbursed are money; the adjustments
    are not money received, whichever sign they carry."""
    _money_and_adjustments()
    from apps.core.management.commands.seed_dd_cards import DD_CARD_CONFIG
    card = DD_CARD_CONFIG.get('cards', DD_CARD_CONFIG)['cash']
    out = card_metrics({'model': 'cash', 'filters': card.get('filters') or {}, 'metrics': card['metrics']}, admin)
    by_label = {m['label']: m['value'] for m in out['metrics']}
    assert by_label['Received'] == 150.0 and by_label['Disbursed'] == -20.0


def test_a_metric_may_exclude(admin):
    _money_and_adjustments()
    out = card_metrics({'model': 'cash', 'metrics': [
        {'field': 'amount', 'agg': 'sum', 'label': 'All', 'exclude': {'method__in': list(ADJUSTMENT_METHODS)}},
        {'field': 'id', 'agg': 'count', 'label': 'Adjustments', 'filters': {'method__in': list(ADJUSTMENT_METHODS)}},
    ]}, admin)
    assert [m['value'] for m in out['metrics']] == [130.0, 5]


def test_the_commerce_dashboard_counts_money_only():
    _money_and_adjustments()
    from apps.core.services.dashboard.dashboard_commerce import get_accounting_dashboard
    out = get_accounting_dashboard({'days': 30})
    cash = out['cash'] if 'cash' in out else out['cash_entries']
    assert float(cash['total']) == 130.0 and cash['count'] == 3


def test_period_close_leaves_adjustments_out_of_cash_received():
    _money_and_adjustments()
    from datetime import datetime, timezone
    from apps.accounts.services.period_close import _generate_period_summary
    today = datetime.now(timezone.utc)
    summary = _generate_period_summary(today.year, today.month)
    assert summary['total_cash_entries'] == 130.0 - 10.0        # money in, less the adjustments (Bill, 2026-09-26)
    assert summary['adjustments'] == {m: 2.0 for m in ADJUSTMENT_METHODS}


@pytest.mark.parametrize('method', ADJUSTMENT_METHODS)
def test_an_adjustment_is_never_reconciled(admin, method):
    cash = _cash(2, method)
    with pytest.raises(Refused) as refused:
        save_record(admin, {'id': cash.pk, 'version': cash.version, 'reconciled': True}, model_key='cash')
    assert refused.value.code == 'not_a_bank_item'
    cash.refresh_from_db()
    assert cash.reconciled is False


def test_a_statement_line_never_names_an_adjustment(admin):
    cash = _cash(2, 'discount')
    from apps.transactions.models import StatementLine
    line = StatementLine.objects.create(description='bank row', amount=Decimal('2'))
    with pytest.raises(Refused) as refused:
        save_record(admin, {'id': line.pk, 'version': line.version, 'cash_id': cash.pk}, model_key='statement_line')
    assert refused.value.code == 'not_a_bank_item'
    money = _cash(2, 'check')
    save_record(admin, {'id': line.pk, 'version': line.version, 'cash_id': money.pk}, model_key='statement_line')
