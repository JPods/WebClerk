from datetime import timedelta

import pytest
from django.utils import timezone

from apps.accounts.services.ledger_balance import on_invoice_save
from apps.core.models import Contact
from apps.orgs.models import OrgBase, OrgType
from apps.transactions.models import Invoice, Cash

pytestmark = pytest.mark.django_db


def test_invoice_gl_accounts_are_staged_as_ar_to_revenue(chart_of_accounts):
    customer_org = OrgBase.objects.create(org_type=OrgType.CUSTOMER, company="Customer Org")

    invoice = Invoice.objects.create(
        status="released",
        customer_id=customer_org.id,
        totals={"total": 250.0, "received": 0.0, "balance": 250.0},
        metadata={},
    )

    on_invoice_save(invoice, replace_ledgers=True)
    invoice.refresh_from_db()

    staged = (invoice.metadata or {}).get("gl_accounts") or {}
    postings = staged.get("postings") or []

    assert staged.get("event") == "invoice_created"
    assert len(postings) == 2
    assert postings[0]["side"] == "debit"
    assert postings[0]["purpose"] == "accounts_receivable"
    assert postings[0]["account"]
    assert postings[1]["side"] == "credit"
    assert postings[1]["purpose"] == "sales_revenue"
    assert postings[1]["account"] == chart_of_accounts["sales_revenue"]


def test_cash_gl_accounts_are_staged_as_cash_to_ar(chart_of_accounts):
    customer_org = OrgBase.objects.create(org_type=OrgType.CUSTOMER, company="Customer Org 2")
    payer = Contact.objects.create(name_first="Jane", name_last="Payer")

    invoice = Invoice.objects.create(
        status="released",
        customer_id=customer_org.id,
        totals={"total": 120.0, "received": 0.0, "balance": 120.0},
        metadata={},
    )

    # CashMethod was removed; Cash.method is a CharField holding the name.
    cash = Cash.objects.create(
        invoice=invoice,
        contact_id=payer.id,
        amount=120.0,
        dt_cash=timezone.now() - timedelta(minutes=1),
        method="Cash",
        status="completed",
        metadata={},
    )
    cash.refresh_from_db()

    staged = (cash.metadata or {}).get("gl_accounts") or {}
    postings = staged.get("postings") or []

    assert staged.get("event") == "cash_received"
    assert len(postings) == 2
    assert postings[0]["side"] == "debit"
    assert postings[0]["purpose"] == "cash_receipt"
    assert postings[0]["account"] == chart_of_accounts["undeposited_funds"]
    assert postings[1]["side"] == "credit"
    assert postings[1]["purpose"] == "accounts_receivable"
    assert postings[1]["account"]
