"""Production is not receiving, and what happens to a line lives on the line.

Completion is the workorder's Complete command (workorder plan, 2026-09-26): the whole build, all
or nothing, once. Bill, 2026-09-27: "One workorder per build … should not allow partials. It will
be less confusing for end users." (Replaces the 09-20 partial completions and complete_workorder.)

A receipt says goods came from outside: it carries a vendor, terms and an AP ledger. A
workorder owes nobody, so its output is an event in ``workorder_line.events[]``, appended
by the pending applier in the same apply that moves the buckets (Bill, 2026-09-20).
"""
from decimal import Decimal

import pytest

from tests.utils import received_receipt_line
from django.apps import apps as dj_apps

pytestmark = pytest.mark.django_db


def _workorder_with_a_line(qty=10):
    from apps.products.models import Item, Warehouse
    from apps.transactions.models import WorkOrder, WorkOrderLine
    item = Item.objects.create(name='Widget', quantity={'on_hand': 0, 'on_wo': 0,
                                                        'allocated': 0, 'available': 0})
    warehouse = Warehouse.objects.create(code='WH1', name='Main')
    wo = WorkOrder.objects.create()
    line = WorkOrderLine.objects.create(
        workorder=wo, line_type='build', item_fk_id=item.pk,
        item={'item_id': item.pk, 'id_num': item.pk, 'description': 'Widget'},
        quantity={'active': qty}, cost={'unit': 4.00, 'precision': 2})
    item.refresh_from_db()
    return wo, line, item, warehouse


def _complete(wo):
    from apps.core.services.door import Actor
    from apps.core.services.verbs import run_command
    return run_command(Actor(kind='system', source='command'), 'complete', 'workorder', wo.pk, {})


def test_completing_a_workorder_makes_stock_and_no_payable():
    from apps.transactions.models import Receipt
    Ledger = dj_apps.get_model('accounts', 'Ledger')
    wo, line, item, warehouse = _workorder_with_a_line(qty=10)
    assert float((item.quantity or {}).get('on_wo')) == 10.0     # the line committed it

    _complete(wo)

    item.refresh_from_db()
    line.refresh_from_db()
    quantity = item.quantity or {}
    assert float(quantity.get('on_wo')) == 0.0        # no longer work in progress
    assert float(quantity.get('on_hand')) == 10.0     # produced
    assert float(quantity.get('on_rc') or 0) == 0.0   # nothing arrived from outside
    assert float((line.quantity or {}).get('remaining')) == 0.0   # the document moved too

    # and nothing that could become money owed
    assert Receipt.objects.count() == 0
    assert Ledger.objects.filter(model_name='receipt').count() == 0
    [event] = line.events
    assert event['kind'] == 'build' and event['qty'] == 10.0
    assert event['consumed']['layers'][0]['layer_id'] == line.inventory_layer_id
    assert event['unit_cost'] == 4.0                  # case 1: the cost entered on the line


def test_a_receipt_without_a_vendor_owes_nobody():
    """The safety net behind the structure: an internal movement writes no AP row."""
    from apps.transactions.models import Receipt, ReceiptLine
    from apps.accounts.services.terms_ledger import apply_terms_for_payable
    Ledger = dj_apps.get_model('accounts', 'Ledger')
    receipt = Receipt.objects.create(source_type=Receipt.SOURCE_ADJUSTMENT)
    received_receipt_line(receipt=receipt, quantity={'active': 2},
                               cost={'unit': 5.00, 'precision': 2})

    rows = apply_terms_for_payable(receipt, replace=True)

    assert rows == []
    assert not Ledger.objects.filter(parent_id=receipt.pk, model_name='receipt').exists()


def test_a_receipt_can_no_longer_claim_to_be_a_workorder():
    from apps.transactions.models import Receipt
    assert not hasattr(Receipt, 'SOURCE_WORKORDER')
    assert [code for code, _label in Receipt.SOURCE_CHOICES] == [
        Receipt.SOURCE_PURCHASE, Receipt.SOURCE_ADJUSTMENT]


# ── a count is a workorder used as an audit tool (Bill, 2026-09-20) ──────


def _item_with_stock(on_hand=10):
    from apps.products.models import Item, Warehouse
    item = Item.objects.create(name='Widget', quantity={'on_hand': on_hand, 'on_wo': 0,
                                                        'allocated': 0, 'available': on_hand})
    warehouse = Warehouse.objects.create(code='WH1', name='Main')
    return item, warehouse


def test_an_event_is_recorded_once_however_often_the_pending_applies():
    """The event id makes an apply idempotent — the guard behind posting through pendings."""
    from apps.core.models import Pending
    wo, line, item, warehouse = _workorder_with_a_line(qty=10)
    _complete(wo)

    line.refresh_from_db()
    assert len(line.events) == 1
    pending = Pending.objects.filter(purpose='inventory_line_add', config__line_id=line.pk,
                                     config__event__kind='build').latest('id')
    pending.dt_processed = 0                 # make it apply again
    pending.try_apply()

    line.refresh_from_db()
    assert len(line.events) == 1             # recorded once


def test_a_workorder_is_completed_once():
    """Bill, 2026-09-27: one workorder per build, no partial completions."""
    from apps.core.services.door import Refused
    wo, line, item, warehouse = _workorder_with_a_line(qty=10)
    _complete(wo)
    with pytest.raises(Refused) as refused:
        _complete(wo)
    assert refused.value.code == 'workorder_complete'
    item.refresh_from_db()
    assert float(item.quantity['on_hand']) == 10.0
