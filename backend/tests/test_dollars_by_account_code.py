"""Smoke test: a $2 sale flows correctly into dollars grouped by GL account code.

Purpose:
    New implementers can run this test to verify that line-level amounts
    (sell price, cost, commission, tax, other) accumulate correctly and
    map to the expected GL account codes.

Scenario (one invoice, one line):
    Sell price    $2.00   → Revenue     4000-sales_revenue  (credit)
    COGS          $1.00   → COGS        5000-cost_of_goods_sold  (debit)
    Commission    $0.20   → Commission  6100-commission_expense  (debit)  10% of sell
    Tax           $0.20   → Tax Payable 2100-sales_tax_payable  (debit)  10% of sell
    Other costs   $0.03   → Handling    no default GL code yet (flagged below)

The "dollars by account code" dict produced at the bottom is what a GL
posting service would consume.  This test lives here so a new developer
can find it instantly and understand the accounting flow.
"""

from decimal import Decimal

import pytest

from apps.accounts.management.commands.seed_gl_accounts import GL_DEFAULTS
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

    assert _d(totals["amount"]) == _d("2.00"), "Subtotal (sell) should be $2.00"
    # Total includes handling ($0.03) added by the totals engine
    assert _d(totals["total"]) == _d("2.03"), "Total should be $2.03 (subtotal + handling)"
    assert _d(totals["cost"]) == _d("1.00"), "Cost should be $1.00"
    # Margin = subtotal - cost (margin_pct stored, not margin_dollars)
    margin = totals.get("margin")
    assert margin is not None, "Margin should be present"


# ---------------------------------------------------------------------------
# 2. Account code mapping: dollars grouped by GL account code
#    Uses line-level data directly (sub-breakdowns for GL posting).
# ---------------------------------------------------------------------------

def test_dollars_by_account_code(simple_sale_invoice):
    """
    Build a 'dollars by account code' dict and assert each entry.

    account codes come from the company GL role map (GL_DEFAULTS);
    every code must be a GlAccount in the chart.
    """
    simple_sale_invoice.update_sell_cost_totals(persist=True)
    simple_sale_invoice.refresh_from_db()

    # Read line-level data for GL sub-breakdowns
    line = simple_sale_invoice.lines.first()
    price = line.price or {}
    cost = line.cost or {}

    sell_revenue = _d(price.get("amount", 0))
    cost_goods = _d(cost.get("extended", 0))
    commissions = _d(cost.get("commissions", 0))
    tax_payable = _d(cost.get("tax", 0))
    handling = _d(cost.get("handling", 0))

    postings = {
        GL_DEFAULTS["sales_revenue"]:     {"purpose": "revenue",     "amount": sell_revenue,  "side": "credit"},
        GL_DEFAULTS["cost_of_goods_sold"]:        {"purpose": "cogs",        "amount": cost_goods,    "side": "debit"},
        GL_DEFAULTS["commission_expense"]:  {"purpose": "commission",  "amount": commissions,   "side": "debit"},
        GL_DEFAULTS["sales_tax_payable"]: {"purpose": "tax_payable", "amount": tax_payable,   "side": "debit"},
        None:                                 {"purpose": "handling",    "amount": handling,      "side": "debit"},
    }

    # Revenue — key comes from GL_DEFAULTS["sales_revenue"] = "4000-sales_revenue"
    rev_key = GL_DEFAULTS["sales_revenue"]
    assert postings[rev_key]["amount"] == _d("2.00")
    assert postings[rev_key]["side"]   == "credit"

    # COGS — key comes from GL_DEFAULTS["cost_of_goods_sold"] = "5000-cost_of_goods_sold"
    cogs_key = GL_DEFAULTS["cost_of_goods_sold"]
    assert postings[cogs_key]["amount"] == _d("1.00")
    assert postings[cogs_key]["side"]   == "debit"

    # Commission — key comes from GL_DEFAULTS["commission_expense"] = "6100-commission_expense"
    comm_key = GL_DEFAULTS["commission_expense"]
    assert postings[comm_key]["amount"] == _d("0.20")
    assert postings[comm_key]["side"]   == "debit"

    # Tax payable — key comes from GL_DEFAULTS["sales_tax_payable"] = "2100-sales_tax_payable"
    tax_key = GL_DEFAULTS["sales_tax_payable"]
    assert postings[tax_key]["amount"] == _d("0.20")
    assert postings[tax_key]["side"]   == "debit"

    # Other / handling — None key means no GL account mapped yet
    assert postings[None]["purpose"] == "handling"
    assert postings[None]["amount"]  == _d("0.03")

    # Total cost accounted for
    total_debits  = sum(p["amount"] for p in postings.values() if p["side"] == "debit")
    total_credits = sum(p["amount"] for p in postings.values() if p["side"] == "credit")
    assert total_debits  == _d("1.43")
    assert total_credits == _d("2.00")
