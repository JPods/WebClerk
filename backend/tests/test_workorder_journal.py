"""A workorder journalizes its events on command (Bill, 2026-09-28/30; GL-by-layer step 6).

Production: parts consumed go into WIP, the build comes out of it at its layer's cost, scrap is
expensed (5300), labor is applied (2160). WIP nets to zero for a complete workorder. Count: found
stock credits shrinkage, missing stock debits it; an opening count credits opening equity.
Each event posts once.
"""
import pytest

from tests.test_stock_count_workorder import _count, _count_wo
from tests.test_stock_layers_follow_sales import _stocked
from tests.test_workorder_build import _run, _wo, cart  # noqa: F401 (fixture)

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures('chart_of_accounts')]


def _net(wo, account):
    from apps.accounts.models import GlJournal
    rows = GlJournal.objects.filter(source_id=wo.pk, source_model__in=('workorder', 'workorder_reversal'),
                                    account=account)
    return round(sum((r.debit or 0) - (r.credit or 0) for r in rows), 2)


def test_a_build_posts_parts_into_wip_and_the_item_out_of_it_with_scrap_expensed(cart):
    wo, line = _wo(cart['cart'], 10)
    _run('expand', wo, line_id=line.pk, depth=0)
    _run('complete', wo)
    wo.refresh_from_db()
    out = _run('journalize', wo)
    assert out['created'] > 0
    assert _net(wo, '1210-work_in_process') == 0.0, 'WIP nets to zero for a complete build'
    assert _net(wo, '5300-scrap_shrinkage') == pytest.approx(4 * 2.0), '4 tires scrapped at 2.00'
    assert _net(wo, '2160-labor_applied') == pytest.approx(-5 * 20.0), '5 h labor at 20.00'
    # Inventory: tires 44 x 2 (4 scrapped), rims 40 x 3, frames 10 x 5 out; 40 wheels at 5.00 in
    # and out; 10 carts at (200 + 50 + 100) / 10 = 35.00 in. Net +92 = labor 100 - scrap 8.
    assert _net(wo, '1200-inventory') == pytest.approx(92.0)


def test_each_event_posts_once():
    from apps.core.services.door import Refused
    item, _ = _stocked()
    wo = _count_wo()
    _count(wo, item, 18, cost=4.0)                      # 3 found at 4.00
    _run('journalize', wo)
    assert _net(wo, '1200-inventory') == 12.0 and _net(wo, '5300-scrap_shrinkage') == -12.0
    with pytest.raises(Refused) as refused:
        _run('journalize', wo)
    assert refused.value.code == 'nothing_to_journalize'


def test_an_opening_count_credits_opening_equity():
    item, _ = _stocked()
    wo = _count_wo(config={'opening': True})
    _count(wo, item, 18, cost=4.0)
    _run('journalize', wo)
    assert _net(wo, '1200-inventory') == 12.0
    assert _net(wo, '3050-opening_balance_equity') == -12.0


def test_unjournalize_reverses_and_the_events_post_again():
    item, _ = _stocked()
    wo = _count_wo()
    _count(wo, item, 18, cost=4.0)
    _run('journalize', wo)
    _run('unjournalize', wo, reason='miscounted')
    assert _net(wo, '1200-inventory') == 0.0
    _run('journalize', wo)
    assert _net(wo, '1200-inventory') == 12.0
