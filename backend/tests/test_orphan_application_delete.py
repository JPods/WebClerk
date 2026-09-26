"""A cash application is permanent — except an orphan on a disposable data set (Bill, 2026-09-26)."""
from decimal import Decimal

import pytest

from apps.core.models.pending import Pending
from apps.orgs.models import OrgBase
from apps.transactions.models import Cash, Invoice, InvoiceLine
from apps.transactions.services.cash import cash_door
from apps.transactions.services.cash.cash_pending import apply_cash_to_invoice
from apps.transactions.services.pricing.totals_compute import recalculate_totals

pytestmark = pytest.mark.django_db


def _application():
    buyer = OrgBase.objects.create(company='Orphan Co', org_type='customer', is_active=True)
    inv = Invoice.objects.create(customer_id=buyer.pk, finance={"sales_tax_rate": 0})
    InvoiceLine.objects.create(invoice=inv, quantity={"active": 1},
                               price={"unit": 20.0, "precision": 2}, cost={"unit": 0})
    recalculate_totals(inv.pk, 'invoice')
    cash = Cash.objects.create(amount=Decimal('20.00'), customer_id=buyer.pk)
    apply_cash_to_invoice(cash.pk, inv.pk, Decimal('20.00'), acted_by=1)
    return Pending.objects.get(purpose='cash_application', changes__invoice_id=inv.pk)


def _orphan(p):
    gone = 10 ** 9
    Pending.objects.filter(pk=p.pk).update(changes={**p.changes, 'invoice_id': gone, 'cash_id': gone})
    p.refresh_from_db()
    return p


def test_a_live_data_set_never_deletes_an_application(monkeypatch):
    monkeypatch.delenv('DATA_SET_KIND', raising=False)
    p = _orphan(_application())
    with pytest.raises(cash_door.CashDoorError, match='live'):
        cash_door.delete_orphan_application(p.pk, 'test')
    assert Pending.objects.filter(pk=p.pk).exists()


def test_an_application_with_a_live_cash_or_invoice_is_refused(monkeypatch):
    monkeypatch.setenv('DATA_SET_KIND', 'demo')
    p = _application()
    with pytest.raises(cash_door.CashDoorError, match='unapply'):
        cash_door.delete_orphan_application(p.pk, 'test')
    assert Pending.objects.filter(pk=p.pk).exists()


def test_a_demo_orphan_is_deleted_and_the_door_still_holds_for_everything_else(monkeypatch):
    monkeypatch.setenv('DATA_SET_KIND', 'demo')
    p = _orphan(_application())
    assert cash_door.delete_orphan_application(p.pk, 'test')['deleted'] == p.pk
    assert not Pending.objects.filter(pk=p.pk).exists()
    other = _application()
    with pytest.raises(cash_door.CashDoorError, match='permanent'):
        other.delete()
