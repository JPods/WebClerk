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
