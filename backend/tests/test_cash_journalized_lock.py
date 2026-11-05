"""A journalized Cash is locked (Bill, 2026-11-05): the journal holds its money. What the bank
reconciliation and the comments add may still change; the rest moves only through its commands."""
from decimal import Decimal

import pytest

from apps.core.services.door import Actor, Refused
from apps.core.services.save import save_record
from apps.transactions.models import Cash

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin(django_user_model):
    return django_user_model.objects.create_superuser(
        email='journal@example.com', password=None, name_first='Jo', name_last='Urnal', username='')


def _journalized():
    return Cash.objects.create(amount=Decimal('100'), available=Decimal('100'), status='complete',
                               reference_number='chk-1', dt_journaled=1793800000000)


def test_a_journalized_cash_refuses_a_change_to_its_money_or_its_facts(admin):
    cash = _journalized()
    for field, value in (('amount', '120'), ('reference_number', 'chk-2'), ('status', 'void')):
        with pytest.raises(Refused) as refused:
            save_record(Actor(user=admin, kind='user'), {'id': cash.pk, 'version': cash.version, field: value}, model_key='cash')
        assert refused.value.code == 'journalized', field
    assert Cash.objects.get(pk=cash.pk).amount == Decimal('100')


def test_reconciliation_and_notes_still_change_on_a_journalized_cash(admin):
    cash = _journalized()
    save_record(Actor(user=admin, kind='user'),
                {'id': cash.pk, 'version': cash.version, 'reconciled': True, 'comments': {'public': 'matched to statement 11/05'}},
                model_key='cash')
    cash.refresh_from_db()
    assert cash.reconciled is True and cash.comments.get('public') == 'matched to statement 11/05'


def test_an_unjournalized_cash_changes_as_before(admin):
    cash = Cash.objects.create(amount=Decimal('100'), available=Decimal('100'), status='planned')
    save_record(Actor(user=admin, kind='user'), {'id': cash.pk, 'version': cash.version, 'reference_number': 'chk-9'}, model_key='cash')
    assert Cash.objects.get(pk=cash.pk).reference_number == 'chk-9'


def test_applying_and_unapplying_a_journalized_cash_still_moves_its_available():
    """The lock is the door's; the cash door's apply and unapply save the derived available and
    status directly and must keep working on a journalized Cash (the lead's check, 2026-11-05)."""
    from apps.core.models.pending import Pending
    from apps.orgs.models import OrgBase
    from apps.transactions.models import Invoice
    from apps.transactions.services.cash.cash_pending import apply_cash_to_invoice, unapply_cash_application
    buyer = OrgBase.objects.create(company='Journal Customer', org_type='customer', is_active=True)
    invoice = Invoice.objects.create(customer_id=buyer.pk, status='open',
                                     totals={'total': 100.0, 'received': 0.0, 'balance': 100.0})
    cash = Cash.objects.create(amount=Decimal('100'), available=Decimal('100'), status='complete', method='check',
                               customer_id=buyer.pk, dt_journaled=1793800000000)
    applied = apply_cash_to_invoice(cash.pk, invoice.pk, Decimal('60.00'))
    cash.refresh_from_db(); invoice.refresh_from_db()
    assert cash.available == Decimal('40.00') and cash.dt_journaled == 1793800000000
    assert Pending.objects.get(pk=applied['pending_id']).changes['state'] == 'applied'
    assert Decimal(str(invoice.totals['received'])) == Decimal('60.00')
    unapply_cash_application(applied['pending_id'], reason='wrong invoice')
    cash.refresh_from_db(); invoice.refresh_from_db()
    assert cash.available == Decimal('100.00')
    assert Decimal(str(invoice.totals['received'])) == Decimal('0.00')
