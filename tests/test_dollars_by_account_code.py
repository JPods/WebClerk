"""Smoke test: a $2 sale flows correctly into dollars grouped by GL account code.

Purpose:
    New implementers can run this test to verify that line-level amounts
    (sell price, cost, commission, tax, other) accumulate correctly and
    map to the expected GL account codes.

Scenario (one invoice, one line):
    Sell price    $2.00   → Revenue     account 4000  (credit)
    COGS          $1.00   → COGS        account 5000  (debit)
    Commission    $0.20   → Commission  account 5200  (debit)  10% of sell
    Tax           $0.20   → Tax Payable account 2100  (debit)  10% of sell
    Other costs   $0.03   → Handling    no default GL code yet (flagged below)

The "dollars by account code" dict produced at the bottom is what a GL
posting service would consume to write GlJournal debit/credit records.
"""
from decimal import Decimal

import pytest

from apps.accounts.services.gl_defaults import FALLBACK_DEFAULTS
from apps.transactions.models import Invoice, InvoiceLine
from apps.transactions.services.invoice_totals import compute_invoice_sell_cost_totals

pytestmark = pytest.mark.django_db


def _d(val) -> Decimal:
    return Decimal(str(val))


@pytest.fixture()
def simple_sale_invoice():
    """One invoice with one line: $2 sell, $1 cost, 10% commission, 10% tax, $0.03 other."""
    invoice = Invoice.objects.create(totals={})
    # quantity=1 unit, price.unit=$2, cost.unit=$1.
    # The model computes extended = quantity.staged × unit on save,
    # so set 'unit' (not 'extended') to get stable values.
    InvoiceLine.objects.create(
        invoice=invoice,
        quantity={"active": 1, "staged": 1},
        price={
            "unit": 2.00,           # → price.extended = $2.00 (Revenue)
        },
        cost={
            "unit": 1.00,           # → cost.extended  = $1.00 (COGS)
            "commissions": 0.20,    # 10% of $2.00 sell
            "tax": 0.20,            # 10% of $2.00 sell
            "handling": 0.03,       # other costs
        },
    )
    return invoice


# ---------------------------------------------------------------------------
# 1. Accumulation: confirm each component sums correctly
# ---------------------------------------------------------------------------

def test_sell_totals(simple_sale_invoice):
    result = compute_invoice_sell_cost_totals(simple_sale_invoice)
    sell = result["sell"]

    assert _d(sell["line_sum_goods"]) == _d("2.00"), "Revenue should be $2.00"
    assert _d(sell["total"]) == _d("2.00")


def test_cost_totals(simple_sale_invoice):
    result = compute_invoice_sell_cost_totals(simple_sale_invoice)
    cost = result["cost"]

    assert _d(cost["line_sum_goods"]) == _d("1.00"), "COGS should be $1.00"
    assert _d(cost["commissions"]) == _d("0.20"),    "Commission should be $0.20"
    assert _d(cost["line_sum_tax"]) == _d("0.20"),   "Tax payable should be $0.20"
    # 'handling' carries the $0.03 other cost
    assert _d(cost["line_sum_handling"]) == _d("0.03"), "Other (handling) should be $0.03"

    expected_total_cost = _d("1.00") + _d("0.20") + _d("0.20") + _d("0.03")
    assert _d(cost["total"]) == expected_total_cost, f"Total cost should be {expected_total_cost}"


def test_margin(simple_sale_invoice):
    result = compute_invoice_sell_cost_totals(simple_sale_invoice)
    totals = result["totals"]

    sell  = _d("2.00")
    costs = _d("1.00") + _d("0.20") + _d("0.20") + _d("0.03")  # $1.43

    assert _d(totals["total"]) == sell
    assert _d(totals["cost"])  == costs
    assert _d(totals["margin"]) == sell - costs  # $0.57


# ---------------------------------------------------------------------------
# 2. Account code mapping: dollars grouped by GL account code
# ---------------------------------------------------------------------------

def test_dollars_by_account_code(simple_sale_invoice):
    """
    Build a 'dollars by account code' dict and assert each entry.

    This is the shape a GL posting service would consume to write
    GlJournal records.  account codes come from FALLBACK_DEFAULTS;
    override them per-tenant via org.gl_accounts or GlAccount records.

    Expected:
        {
            '4000': {'purpose': 'revenue',     'amount':  2.00, 'side': 'credit'},
            '5000': {'purpose': 'cogs',        'amount':  1.00, 'side': 'debit'},
            '5200': {'purpose': 'commission',  'amount':  0.20, 'side': 'debit'},
            '2100': {'purpose': 'tax_payable', 'amount':  0.20, 'side': 'debit'},
            None:   {'purpose': 'handling',    'amount':  0.03, 'side': 'debit'},  # no default yet
        }
    """
    result = compute_invoice_sell_cost_totals(simple_sale_invoice)
    sell = result["sell"]
    cost = result["cost"]

    # Build the posting map  (purpose → account code → dollars)
    # Use FALLBACK_DEFAULTS; in production these are overridden by
    # org.gl_accounts or active GlAccount records.
    postings = {
        FALLBACK_DEFAULTS.get("revenue"):     {"purpose": "revenue",     "amount": _d(sell["line_sum_goods"]), "side": "credit"},
        FALLBACK_DEFAULTS.get("cogs"):        {"purpose": "cogs",        "amount": _d(cost["line_sum_goods"]), "side": "debit"},
        FALLBACK_DEFAULTS.get("commission"):  {"purpose": "commission",  "amount": _d(cost["commissions"]),    "side": "debit"},
        FALLBACK_DEFAULTS.get("tax_payable"): {"purpose": "tax_payable", "amount": _d(cost["line_sum_tax"]),   "side": "debit"},
        # 'handling' has no fallback GL code yet — None key flags it for wiring up
        None:                                 {"purpose": "handling",    "amount": _d(cost["line_sum_handling"]), "side": "debit"},
    }

    # Revenue (account 4000)
    assert postings["4000"]["amount"] == _d("2.00")
    assert postings["4000"]["side"]   == "credit"

    # COGS (account 5000)
    assert postings["5000"]["amount"] == _d("1.00")
    assert postings["5000"]["side"]   == "debit"

    # Commission (account 5200)
    assert postings["5200"]["amount"] == _d("0.20")
    assert postings["5200"]["side"]   == "debit"

    # Tax payable (account 2100)
    assert postings["2100"]["amount"] == _d("0.20")
    assert postings["2100"]["side"]   == "debit"

    # Other / handling — None key means no GL account mapped yet
    assert postings[None]["purpose"] == "handling"
    assert postings[None]["amount"]  == _d("0.03")

    # Total cost accounted for
    total_debits  = sum(p["amount"] for p in postings.values() if p["side"] == "debit")
    total_credits = sum(p["amount"] for p in postings.values() if p["side"] == "credit")
    # Cost components sum to $1.43 (COGS $1.00 + commission $0.20 + tax $0.20 + other $0.03)
    assert total_debits  == _d("1.43")
    # Revenue credit is $2.00
    assert total_credits == _d("2.00")
    # Gross margin = credits − debits = $0.57
    assert total_credits - total_debits == _d("0.57")
    # Note: A full balanced journal entry also needs AR debit $2.00 and
    # Inventory/AP credit $1.43.  Those contra entries belong in a GL
    # posting service, not in this accumulation smoke test.
