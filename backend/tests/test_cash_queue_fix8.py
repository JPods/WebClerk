"""Fix #8 (Fable L1 H-1, L1 M-8, L2 H-4): a cash application queues only on a locked row,
counts its attempts, and the drain lands it. Any other failure raises (Axiom 6)."""
from decimal import Decimal

import pytest
from django.db import OperationalError

from apps.core.models.pending import Pending
from apps.orgs.models import OrgBase
from apps.transactions.models import Cash, Invoice, InvoiceLine
from apps.transactions.services.cash import cash_pending
from apps.transactions.services.pricing.totals_compute import recalculate_totals

pytestmark = pytest.mark.django_db


def _setup(amount='25.00'):
    buyer = OrgBase.objects.create(company='Queue Buyer', org_type='customer', is_active=True)
    inv = Invoice.objects.create(customer_id=buyer.pk, finance={"sales_tax_rate": 0})
    InvoiceLine.objects.create(invoice=inv, quantity={"active": 1},
                               price={"unit": 100.0, "precision": 2}, cost={"unit": 0})
    recalculate_totals(inv.pk, 'invoice')
    cash = Cash.objects.create(amount=Decimal(amount), customer_id=buyer.pk)
    return inv, cash


def test_a_real_failure_raises_and_leaves_nothing_counted_against_the_cash(monkeypatch):
    inv, cash = _setup()
    def boom(pending):
        raise RuntimeError('a bug in a receiver')
    monkeypatch.setattr(cash_pending, 'apply_cash_pending', boom)
    with pytest.raises(RuntimeError, match='a bug'):
        cash_pending.apply_cash_to_invoice(cash.pk, inv.pk, Decimal('25.00'), acted_by=1)
    assert not Pending.objects.filter(purpose='cash_application', changes__invoice_id=inv.pk).exists(), \
        'no application sits queued, spending cash that never moved'


def test_a_locked_row_queues_counts_the_attempt_and_the_drain_lands_it(monkeypatch):
    inv, cash = _setup()
    real = cash_pending.apply_cash_pending
    monkeypatch.setattr(cash_pending, 'apply_cash_pending',
                        lambda p: (_ for _ in ()).throw(OperationalError('could not obtain lock')))
    result = cash_pending.apply_cash_to_invoice(cash.pk, inv.pk, Decimal('25.00'), acted_by=1)
    assert result['applied'] is False
    p = Pending.objects.get(purpose='cash_application', changes__invoice_id=inv.pk)
    assert p.dt_processed == 0 and p.attempts == 1

    monkeypatch.setattr(cash_pending, 'apply_cash_pending', real)
    assert cash_pending.drain_queued_cash() == {'applied': 1, 'queued': 0}
    inv.refresh_from_db(); cash.refresh_from_db(); p.refresh_from_db()
    assert p.dt_processed > 0
    assert inv.totals['received'] == 25.0 and cash.available == Decimal('0.00')


def test_the_drain_is_scheduled_every_minute():
    from apps.support.scheduler.registry import build_celery_beat_schedule
    entry = build_celery_beat_schedule()['drain-queued-cash-every-minute']
    assert entry['task'].endswith('task_drain_queued_cash')
