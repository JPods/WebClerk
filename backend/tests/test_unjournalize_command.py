"""Unjournalize stays, and is glaring — plan §16d (Bill, 2026-09-26).

A journalized record is corrected by an amending document; unjournalizing is still possible, as
a command on the record with a reason, stamped in comments.process for Alice to count.
"""
import pytest

pytestmark = pytest.mark.django_db


def _journalized_invoice():
    from apps.orgs.models import OrgBase
    from apps.transactions.models import Invoice
    buyer = OrgBase.objects.create(company='Buyer', org_type='customer', is_active=True)
    invoice = Invoice.objects.create(customer_id=buyer.pk, finance={'sales_tax_rate': 0})
    Invoice.objects.filter(pk=invoice.pk).update(dt_journaled=1790000000000)
    return invoice


def _run(invoice, payload):
    from apps.core.services.door import Actor
    from apps.core.services.verbs import run_command
    return run_command(Actor(kind='system', source='command'), 'unjournalize', 'invoice', invoice.pk, payload)


def test_unjournalize_needs_a_reason():
    from apps.core.services.door import Refused
    invoice = _journalized_invoice()
    with pytest.raises(Refused) as refused:
        _run(invoice, {})
    assert refused.value.code == 'reason_required'


def test_unjournalize_unlocks_and_leaves_its_mark():
    invoice = _journalized_invoice()
    out = _run(invoice, {'reason': 'wrong customer'})
    invoice.refresh_from_db()
    assert out['reason'] == 'wrong customer'
    assert invoice.dt_journaled == 0
    [entry] = invoice.comments['process']
    assert entry['source'] == 'unjournalize' and 'wrong customer' in entry['mgs']


def test_unjournalizing_what_is_not_journalized_is_refused():
    from apps.core.services.door import Refused
    invoice = _journalized_invoice()
    _run(invoice, {'reason': 'first'})
    with pytest.raises(Refused) as refused:
        _run(invoice, {'reason': 'again'})
    assert refused.value.code == 'not_journalized'
