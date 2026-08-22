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
posting service would consume.  This test lives here so a new developer
can find it instantly and understand the accounting flow.
"""

from decimal import Decimal

import pytest

from apps.accounts.services.gl_defaults import FALLBACK_DEFAULTS
from apps.transactions.models import Invoice, InvoiceLine

pytestmark = pytest.mark.django_db


def _d(val) -> Decimal:
    return Decimal(str(val))


@pytest.fixture()
def simple_sale_invoice():
    """One invoice with one line: $2 sell, $1 cost, 10% commission, 10% tax, $0.03 other."""
    invoice = Invoice.objects.create(totals={})
    InvoiceLine.objects.create(
        invoice=invoice,
        quantity={"active": 1, "staged": 1},
        price={
            "unit": 2.00,
        },
        cost={
            "unit": 1.00,
            "commissions": 0.20,
            "tax": 0.20,
            "handling": 0.03,
        },
    )
    return invoice


# ---------------------------------------------------------------------------
# 1. Totals via unified engine
# ---------------------------------------------------------------------------

def test_totals(simple_sale_invoice):
    simple_sale_invoice.update_sell_cost_totals(persist=True)
    simple_sale_invoice.refresh_from_db()
    totals = simple_sale_invoice.totals

    assert _d(totals["subtotal"]) == _d("2.00"), "Subtotal (sell) should be $2.00"
    assert _d(totals["total"]) == _d("2.00"), "Total should be $2.00"
    assert _d(totals["cost"]) == _d("1.00"), "Cost should be $1.00"
    assert _d(totals["margin"]) == _d("1.00"), "Margin should be $1.00"


# ---------------------------------------------------------------------------
# 2. Account code mapping: dollars grouped by GL account code
#    Uses line-level data directly (sub-breakdowns for GL posting).
# ---------------------------------------------------------------------------

def test_dollars_by_account_code(simple_sale_invoice):
    """
    Build a 'dollars by account code' dict and assert each entry.

    account codes come from FALLBACK_DEFAULTS;
    override them per-tenant via org.gl_accounts or GlAccount records.
    """
    simple_sale_invoice.update_sell_cost_totals(persist=True)
    simple_sale_invoice.refresh_from_db()

    # Read line-level data for GL sub-breakdowns
    line = simple_sale_invoice.lines.first()
    price = line.price or {}
    cost = line.cost or {}

    sell_revenue = _d(price.get("extended", 0))
    cost_goods = _d(cost.get("extended", 0))
    commissions = _d(cost.get("commissions", 0))
    tax_payable = _d(cost.get("tax", 0))
    handling = _d(cost.get("handling", 0))

    postings = {
        FALLBACK_DEFAULTS.get("revenue"):     {"purpose": "revenue",     "amount": sell_revenue,  "side": "credit"},
        FALLBACK_DEFAULTS.get("cogs"):        {"purpose": "cogs",        "amount": cost_goods,    "side": "debit"},
        FALLBACK_DEFAULTS.get("commission"):  {"purpose": "commission",  "amount": commissions,   "side": "debit"},
        FALLBACK_DEFAULTS.get("tax_payable"): {"purpose": "tax_payable", "amount": tax_payable,   "side": "debit"},
        None:                                 {"purpose": "handling",    "amount": handling,      "side": "debit"},
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
    assert total_debits  == _d("1.43")
    assert total_credits == _d("2.00")
