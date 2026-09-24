"""Two totals defects, tested on the pure calculation.

B-4 (2026-09-23): an exempt customer was taxed at a rate typed on the line — the typed
rate was checked before the exemption. Exemption comes first.

B1 (2026-09-23): a document with allocations (shipping, other, a discount, landed costs)
and no product line spread them over nothing; they vanished from the totals. Bill:
refuse the save, and name the allocation.
"""
from types import SimpleNamespace

import pytest

from apps.core.services.door import Refused
from apps.transactions.services.pricing.totals_compute import compute_totals

pytestmark = pytest.mark.django_db   # the tax policy is a Setting


def _header(**kw):
    base = dict(finance={'sales_tax_rate': 8.25}, tax={}, allocations={}, customer_id=None,
                ship_via='')
    base.update(kw)
    return SimpleNamespace(**base)


def _line(pk=1, unit=100.0, qty=1, tax=None, line_type='product'):
    return SimpleNamespace(pk=pk, line_number=pk, line_type=line_type, is_active=True,
                           quantity={'active': qty}, price={'unit': unit, 'precision': 2},
                           cost={}, tax=tax or {})


# ── B-4 ───────────────────────────────────────────────────────────────

def test_an_exempt_customer_is_not_taxed_at_a_rate_typed_on_the_line():
    header = _header(finance={'sales_tax_rate': 8.25, 'tax_exempt': True})
    typed = _line(tax={'sales_rate': 7.0, 'rate_source': 'line'})

    result = compute_totals(header, [typed], 'invoice')

    lt = result['line_totals'][typed.pk] if typed.pk in result['line_totals'] \
        else next(iter(result['line_totals'].values()))
    assert float(lt['tax']) == 0.0
    assert lt['rate_source'] == 'exempt'


def test_a_rate_typed_on_the_line_still_applies_to_a_taxable_customer():
    typed = _line(tax={'sales_rate': 7.0, 'rate_source': 'line'})
    result = compute_totals(_header(), [typed], 'invoice')
    lt = next(iter(result['line_totals'].values()))
    assert lt['rate_source'] == 'line' and float(lt['tax']) == 7.0


# ── B1 ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize('alloc,named', [
    ({'shipping': 12.5}, 'shipping'),
    ({'other': 3}, 'other'),
    ({'discount_amount': 10}, 'discount_amount'),
    ({'discount_percent': 5}, 'discount_percent'),
])
def test_an_allocation_with_no_product_line_is_refused_by_name(alloc, named):
    note = _line(line_type='comment', unit=0)
    with pytest.raises(Refused) as caught:
        compute_totals(_header(allocations=alloc), [note], 'invoice')
    assert caught.value.status == 400
    assert caught.value.code == 'allocations_without_product_line'
    assert caught.value.details['allocations'] == [named]
    assert named in caught.value.message


def test_a_receipts_landed_cost_with_no_product_line_is_refused():
    with pytest.raises(Refused) as caught:
        compute_totals(_header(allocations={'freight': 40}), [], 'receipt')
    assert 'freight' in caught.value.details['allocations']


def test_no_allocations_and_no_lines_is_simply_zero():
    result = compute_totals(_header(), [], 'invoice')
    assert float(result['totals'].get('total', 0) or 0) == 0.0


def test_allocations_with_a_product_line_spread_as_before():
    result = compute_totals(_header(allocations={'shipping': 12.5}), [_line()], 'invoice')
    lt = next(iter(result['line_totals'].values()))
    assert float(lt['shipping']) == 12.5
