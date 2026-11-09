"""The browser's totals must equal the server's (Bill, 2026-11-08; readme 107).

This test is the match guarantee. Every case below is run through compute_totals — the one
engine the save runs — and the answers are written to the frontend's fixture,
frontend/src/apps/transactions/services/__tests__/fixtures/totals_cases.json, which the vitest
alignment test replays against the browser engine (totalsCompute.ts), expecting the same
figures exactly.

    WC_TOTALS_FIXTURE_WRITE=1 pytest tests/test_totals_fixture.py     # regenerate the fixture

Without the flag, the test asserts the fixture on disk is what compute_totals produces now: a
change to the server's rule without a regenerated fixture fails here, and the regenerated
fixture then fails vitest until the browser follows. Nothing here touches the database: the
three outside lookups (tax policy, shipping services, customer exemption) and the settlement
figures come from each case's `context`, exactly as the browser receives them.

The first case is the live drift that opened this file: a unit of 8.575 is 8.58 on the server
(Decimal, half-up) and was 8.57 in the browser's float round().
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from apps.transactions.services.pricing import totals_compute
from apps.transactions.services.fulfillment import fulfillment_freight

FIXTURE = (Path(__file__).resolve().parents[2] / 'frontend' / 'src' / 'apps' / 'transactions'
           / 'services' / '__tests__' / 'fixtures' / 'totals_cases.json')

HEADER_KEYS = ('finance', 'tax', 'allocations', 'ship_via', 'customer_id')
LINE_KEYS = ('line_type', 'line_number', 'quantity', 'price', 'cost', 'tax', 'physical', 'is_active')

NO_SETTLEMENT = {'received': 0, 'adjusted': 0, 'settled': 0}
TAX10 = {'sales_tax_rate': 10}
UPS = [{'name': 'UPS Ground', 'carrier_code': 'UPSG', 'aliases': ['ups'],
        'rate_method': 'percent_of_goods', 'rate_percent': 4},
       {'name': 'Pickup', 'rate_method': 'flat', 'rate_percent': 0}]


def line(n, qty, unit, *, cost=None, line_type='product', precision=2, pct=0, flat=0,
         cost_pct=0, cost_flat=0, tax=None, tax_code=None, weight=None, pins=None,
         is_active=True, ship=0, handling=0, cost_precision=2, side='sell'):
    """A line as the screen holds it. `side` says which envelope carries `unit`."""
    price_env = {'unit': unit, 'precision': precision, 'discount_percent': pct, 'discount_amount': flat}
    cost_env = {'unit': cost if cost is not None else 0, 'precision': cost_precision,
                'discount_percent': cost_pct, 'discount_amount': cost_flat,
                'shipping': ship, 'handling': handling}
    if side == 'buy':
        cost_env = {**cost_env, 'unit': unit, 'precision': precision,
                    'discount_percent': pct, 'discount_amount': flat}
        price_env = None
    if tax_code:
        cost_env['tax_code'] = tax_code
    if pins:
        cost_env['landed_override'] = pins
    return {'id': 100 + n, 'line_number': n, 'line_type': line_type,
            'quantity': {'active': qty}, 'price': price_env, 'cost': cost_env,
            'tax': tax, 'physical': {'weight': weight} if weight else None, 'is_active': is_active}


def case(name, model, lines, *, finance=None, tax=None, allocations=None, ship_via='',
         customer_id=None, policy=None, services=None, exempt=False, settlement=None, stored=None):
    return {
        'name': name, 'model': model,
        'header': {'finance': finance or {}, 'tax': tax or {}, 'allocations': allocations or {},
                   'ship_via': ship_via, 'customer_id': customer_id, 'totals': stored or {}},
        'lines': lines,
        'context': {'tax_policy': policy or {}, 'shipping_services': services or [],
                    'customer_exempt': exempt, 'settlement': settlement or NO_SETTLEMENT},
    }


CASES = [
    # ── The live drift first: half-up where float round() went down ──
    case('half_up_8575_drift', 'order', [line(1, 1, 8.575)], finance=TAX10),
    case('half_up_boundaries', 'order',
         [line(1, 1, 1.005), line(2, 1, 2.675), line(3, 1, 1.045), line(4, 1, 0.125)], finance=TAX10),
    case('qty_six_places', 'quote', [line(1, 2.123456, 12.71, cost=8.97), line(2, 0.000001, 1000000)],
         finance=TAX10),
    case('precision_three_and_zero', 'order',
         [line(1, 3, 33.333, precision=3, cost=10, cost_precision=0), line(2, 7, 8.975, cost=7.777, cost_precision=0)],
         finance=TAX10),

    # ── Line discounts: the larger of pct and flat; discounted unit first ──
    case('line_pct_vs_flat_larger_wins', 'order',
         [line(1, 10, 100, pct=10, flat=50, cost=60), line(2, 5, 200, pct=10, flat=150, cost=80),
          line(3, 3, 9.99, pct=12.5, cost=4.44, cost_pct=5)],
         finance=TAX10),
    case('flat_discount_per_unit_rounds', 'invoice', [line(1, 3, 10, flat=1, cost=5)], finance=TAX10),
    case('zero_quantity_line', 'order', [line(1, 0, 100, flat=5, cost=50), line(2, 1, 10)], finance=TAX10),

    # ── Document allocations over the product lines ──
    case('doc_discount_percent', 'order',
         [line(1, 2, 19.99, cost=9), line(2, 1, 5.55, cost=3)],
         finance=TAX10, allocations={'discount_percent': 7.5}),
    case('doc_discount_flat_remainder_last_line', 'order',
         [line(1, 1, 10, cost=4), line(2, 1, 10, cost=4), line(3, 1, 10, cost=4)],
         finance=TAX10, allocations={'discount_amount': 1}),
    case('doc_discount_both_larger_applies', 'order',
         [line(1, 4, 25, cost=10), line(2, 2, 50, cost=20)],
         finance=TAX10, allocations={'discount_percent': 10, 'discount_amount': 15}),
    case('doc_discount_both_pct_wins', 'order',
         [line(1, 4, 25, cost=10), line(2, 2, 50, cost=20)],
         finance=TAX10, allocations={'discount_percent': 10, 'discount_amount': 5}),
    case('shipping_other_remainders', 'order',
         [line(1, 1, 10), line(2, 1, 10), line(3, 1, 10)],
         finance=TAX10, allocations={'shipping': 10, 'other': 0.02}),
    case('ship_via_percent_of_goods', 'invoice',
         [line(1, 3, 12.71, cost=8.97), line(2, 1, 0.37)],
         finance=TAX10, ship_via='ups', services=UPS, allocations={'shipping': 5}),
    case('ship_via_not_percent', 'invoice', [line(1, 3, 12.71)], finance=TAX10, ship_via='Pickup', services=UPS),
    case('line_shipping_and_handling_envelope', 'order',
         [line(1, 2, 10, ship=3.5, handling=1.25)], finance=TAX10),

    # ── Tax: every source ──
    case('tax_header_rate_as_fraction', 'order', [line(1, 1, 100)], finance={'sales_tax_rate': 0.0825}),
    case('tax_header_rate_as_percent', 'order', [line(1, 1, 100)], finance={'sales_tax_rate': 8.25}),
    case('tax_typed_on_line', 'order',
         [line(1, 1, 100, tax={'sales_rate': 5, 'rate_source': 'line'}),
          line(2, 1, 100, tax={'sales_rate': 0.02, 'rate_source': 'line'}), line(3, 1, 100)],
         finance=TAX10),
    case('tax_item_exempt_code', 'order',
         [line(1, 1, 100, tax_code='exempt'), line(2, 1, 100, tax_code='NON-TAXABLE'), line(3, 1, 100)],
         finance=TAX10),
    case('tax_exempt_customer_overrides_typed_rate', 'invoice',
         [line(1, 1, 100, tax={'sales_rate': 5, 'rate_source': 'line'})], finance=TAX10, exempt=True),
    case('tax_exempt_code_on_header', 'invoice', [line(1, 1, 100)], finance=TAX10, tax={'exempt_code': 'RESALE'}),
    case('tax_costs_not_taxed_on_purchase', 'purchase', [line(1, 2, 8.97, side='buy')], finance=TAX10),
    case('tax_on_costs_when_policy_says', 'purchase', [line(1, 2, 8.97, side='buy')],
         finance=TAX10, policy={'tax_on_costs': True}),
    case('tax_on_shipping_when_policy_says', 'order',
         [line(1, 1, 100), line(2, 1, 50)],
         finance=TAX10, tax={'shipping': 6}, allocations={'shipping': 9.99}, policy={'tax_on_shipping': True}),
    case('tax_on_shipping_off_by_default', 'order',
         [line(1, 1, 100)], finance=TAX10, tax={'shipping': 6}, allocations={'shipping': 9.99}),
    case('header_rate_changed_lines_carry_stale_totals', 'order',
         [{**line(1, 2, 10), 'totals': {'tax': 99, 'amount': 99, 'total': 999}}], finance={'sales_tax_rate': 7}),

    # ── Non-product lines ──
    case('non_product_lines', 'invoice',
         [line(1, 1, 100, cost=40), line(2, 1, 7.5, line_type='tax'), line(3, 1, 12, line_type='shipping'),
          line(4, 1, 2.5, line_type='finance_charge'), line(5, 1, 3, line_type='discount')],
         finance=TAX10),
    case('discount_line_on_buy_side_is_nothing', 'purchase',
         [line(1, 1, 100, side='buy'), line(2, 1, 3, line_type='discount', side='buy')]),
    case('inactive_line_excluded', 'order',
         [line(1, 1, 100), line(2, 1, 50, is_active=False), line(3, 1, 25)], finance=TAX10),

    # ── Settlement and state ──
    case('invoice_partial_payment', 'invoice', [line(1, 1, 100, cost=40)], finance=TAX10,
         settlement={'received': 60, 'adjusted': 0.5, 'settled': 60}),
    case('invoice_paid', 'invoice', [line(1, 1, 100)], finance=TAX10,
         settlement={'received': 110, 'adjusted': 0, 'settled': 110}),
    case('invoice_over_paid', 'invoice', [line(1, 1, 100)], finance=TAX10,
         settlement={'received': 120, 'adjusted': 0, 'settled': 120}),
    case('credit_memo_negative', 'invoice', [line(1, -2, 12.71, cost=8.97), line(2, 1, 0.37)], finance=TAX10),
    case('credit_memo_with_credit_state', 'invoice', [line(1, -1, 50)]),

    # ── Receipts: landed costs, the most cases (lead, 2026-11-08) ──
    case('landed_by_value_default', 'receipt',
         [line(1, 3, 10, side='buy'), line(2, 1, 5, side='buy'), line(3, 2, 7.5, side='buy')],
         allocations={'freight': 10, 'duty': 2.5, 'handling': 0.03, 'vat': 0},
         settlement={'received': 0, 'adjusted': 0, 'settled': 0}),
    case('landed_by_weight_mixed_units', 'receipt',
         [line(1, 2, 10, side='buy', weight={'value': 1.5, 'unit': 'kg'}),
          line(2, 4, 5, side='buy', weight={'value': 12, 'unit': 'oz'}),
          line(3, 1, 7.5, side='buy', weight={'value': 3.3, 'unit': 'lb'})],
         allocations={'freight': 25, 'method': {'freight': 'weight'}}),
    case('landed_by_weight_missing_falls_to_value', 'receipt',
         [line(1, 2, 10, side='buy', weight={'value': 1.5, 'unit': 'kg'}), line(2, 4, 5, side='buy')],
         allocations={'freight': 25, 'method': {'freight': 'weight'}}),
    case('landed_by_quantity', 'receipt',
         [line(1, 3, 10, side='buy'), line(2, 1, 5, side='buy'), line(3, 2, 7.5, side='buy')],
         allocations={'duty': 10, 'method': {'duty': 'quantity'}}),
    case('landed_pins_one_line_rest_spreads', 'receipt',
         [line(1, 3, 10, side='buy', pins={'freight': 4}), line(2, 1, 5, side='buy'), line(3, 2, 7.5, side='buy')],
         allocations={'freight': 10, 'method': {'freight': 'value'}}),
    case('landed_all_pinned_adding_up', 'receipt',
         [line(1, 1, 10, side='buy', pins={'duty': 1.5}), line(2, 1, 5, side='buy', pins={'duty': 0.5})],
         allocations={'duty': 2}),
    case('landed_remainder_cent_on_last_line', 'receipt',
         [line(1, 1, 10, side='buy'), line(2, 1, 10, side='buy'), line(3, 1, 10, side='buy')],
         allocations={'freight': 10, 'vat': 0.01}),
    case('landed_each_component_by_its_own_basis', 'receipt',
         [line(1, 2, 10, side='buy', weight={'value': 1, 'unit': 'kg'}),
          line(2, 1, 30, side='buy', weight={'value': 4, 'unit': 'kg'})],
         allocations={'freight': 6, 'duty': 6, 'handling': 6, 'vat': 6,
                      'method': {'freight': 'weight', 'duty': 'value', 'handling': 'quantity'}},
         settlement={'received': 0, 'adjusted': 1.25, 'settled': 20}),
    case('receipt_with_line_discounts_and_tax_on_costs', 'receipt',
         [line(1, 10, 8.975, side='buy', pct=10), line(2, 2, 100, side='buy', flat=15)],
         finance=TAX10, policy={'tax_on_costs': True}, allocations={'freight': 7.77}),
]


def _run(c):
    """compute_totals on a case, every outside lookup answered from its context."""
    ctx = c['context']
    header = SimpleNamespace(pk=None, totals=c['header'].get('totals') or {},
                             **{k: c['header'].get(k) for k in HEADER_KEYS})
    rows = [SimpleNamespace(pk=l['id'], **{k: l.get(k, True if k == 'is_active' else None) for k in LINE_KEYS})
            for l in c['lines']]
    st = ctx['settlement']
    saved = (totals_compute._customer_is_exempt, totals_compute._tax_policy, totals_compute._settlement,
             fulfillment_freight.shipping_service_for)
    totals_compute._customer_is_exempt = lambda customer_id: bool(ctx['customer_exempt'])
    totals_compute._tax_policy = lambda: {'tax_on_shipping': bool(ctx['tax_policy'].get('tax_on_shipping')),
                                          'tax_on_costs': bool(ctx['tax_policy'].get('tax_on_costs'))}
    totals_compute._settlement = lambda h, m: (totals_compute._d(st['received']), totals_compute._d(st['adjusted']),
                                               totals_compute._d(st['settled']))
    fulfillment_freight.shipping_service_for = lambda ship_via: _service(ship_via, ctx['shipping_services'])
    try:
        computed = totals_compute.compute_totals(header, rows, c['model'])
    finally:
        (totals_compute._customer_is_exempt, totals_compute._tax_policy, totals_compute._settlement,
         fulfillment_freight.shipping_service_for) = saved
    return {'totals': _plain(computed['totals']),
            'line_totals': [_plain(computed['line_totals'].get(r.pk)) for r in rows]}


def _service(ship_via, services):
    wanted = (ship_via or '').strip().lower()
    for svc in services:
        keys = {str(svc.get(k) or '').strip().lower() for k in ('name', 'carrier_code', 'account')}
        keys |= {str(a).strip().lower() for a in (svc.get('aliases') or [])}
        if wanted and wanted in keys:
            return svc
    return None


def _plain(value):
    """JSON-ready, with -0.0 made 0.0 (JS deep equality tells them apart)."""
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, float):
        return value + 0.0
    return value


def generate():
    return {'generated_by': 'backend/tests/test_totals_fixture.py (WC_TOTALS_FIXTURE_WRITE=1)',
            'cases': [{**c, 'expect': _run(c)} for c in CASES]}


@pytest.mark.parametrize('c', CASES, ids=[c['name'] for c in CASES])
def test_every_case_computes(c):
    expect = _run(c)
    assert set(expect['totals']) >= {'amount', 'tax', 'total', 'balance'}
    assert len(expect['line_totals']) == len(c['lines'])


def test_first_case_is_the_half_up_drift():
    expect = _run(CASES[0])
    assert CASES[0]['name'] == 'half_up_8575_drift'
    assert expect['line_totals'][0]['discounted_unit'] == 8.58
    assert expect['totals']['amount'] == 8.58


def test_fixture_on_disk_is_current():
    """The browser replays this file; it must be what the server computes now."""
    fresh = generate()
    if os.environ.get('WC_TOTALS_FIXTURE_WRITE'):
        FIXTURE.parent.mkdir(parents=True, exist_ok=True)
        FIXTURE.write_text(json.dumps(fresh, indent=1, sort_keys=False) + '\n')
    assert FIXTURE.exists(), f'{FIXTURE} is missing — run with WC_TOTALS_FIXTURE_WRITE=1'
    on_disk = json.loads(FIXTURE.read_text())
    assert on_disk == json.loads(json.dumps(fresh)), (
        'compute_totals changed: regenerate with WC_TOTALS_FIXTURE_WRITE=1 and make the browser follow')
