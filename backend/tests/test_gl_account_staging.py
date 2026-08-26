from datetime import timedelta

import pytest
from django.utils import timezone

from apps.accounts.services.ledger_balance import on_invoice_save
from apps.core.models import Contact
from apps.orgs.models import OrgBase, OrgType
from apps.orgs.services.primary_org import set_primary_org
from apps.transactions.models import Invoice, Payment, PaymentMethod

pytestmark = pytest.mark.django_db


def _setup_primary_org_defaults() -> None:
    primary = OrgBase.objects.create(
        org_type=OrgType.CUSTOMER,
        display_name="Primary Org",
        gl_accounts={
            "sales": "REV-SALES-000",
            "inventory": "ASSET-INVENTORY-000",
            "cogs": "COGS-PRODUCTS-000",
            "purchase": "LIAB-AP-000",
        },
    )
    set_primary_org(primary)


def test_invoice_gl_accounts_are_staged_as_ar_to_revenue():
    _setup_primary_org_defaults()
    customer_org = OrgBase.objects.create(org_type=OrgType.CUSTOMER, display_name="Customer Org")

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
    assert postings[1]["account"] == "REV-SALES-000"


def test_payment_gl_accounts_are_staged_as_cash_to_ar():
    _setup_primary_org_defaults()
    customer_org = OrgBase.objects.create(org_type=OrgType.CUSTOMER, display_name="Customer Org 2")
    payer = Contact.objects.create(name_first="Jane", name_last="Payer")

    invoice = Invoice.objects.create(
        status="released",
        customer_id=customer_org.id,
        totals={"total": 120.0, "received": 0.0, "balance": 120.0},
        metadata={},
    )

    payment_method = PaymentMethod.objects.create(
        name="Cash",
        metadata={"gl_accounts": {"receipt": "ASSET-CASH-000"}},
    )

    payment = Payment.objects.create(
        invoice=invoice,
        contact=payer,
        amount=120.0,
        dt_payment=timezone.now() - timedelta(minutes=1),
        method=payment_method.name,
        status="completed",
        metadata={},
    )
    payment.refresh_from_db()

    staged = (payment.metadata or {}).get("gl_accounts") or {}
    postings = staged.get("postings") or []

    assert staged.get("event") == "payment_received"
    assert len(postings) == 2
    assert postings[0]["side"] == "debit"
    assert postings[0]["purpose"] == "cash_receipt"
    assert postings[0]["account"] == "ASSET-CASH-000"
    assert postings[1]["side"] == "credit"
    assert postings[1]["purpose"] == "accounts_receivable"
    assert postings[1]["account"]
