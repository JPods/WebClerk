import pytest
from rest_framework.test import APIClient

from apps.core.models.setting import Setting
from apps.transactions.models.line_variants import (
    Proposal, ProposalLine,
    SalesOrder, SalesOrderLine,
    PurchaseOrder, PurchaseOrderLine,
)
from apps.products.models.item import Item
from apps.products.models.warehouse import Warehouse


def _auth(user):
    from rest_framework_simplejwt.tokens import RefreshToken
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f'Bearer {RefreshToken.for_user(user).access_token}')
    return c


@pytest.mark.django_db
def test_proposal_to_sales_order_action(django_user_model):
    # Minimal permission rules for Proposal (header) actions
    Setting.objects.create(
        purpose='view_edit', model_name='proposal', is_active=True,
        data={"USER": {"view": ["id"], "edit": ["id"]}}
    )
    user = django_user_model.objects.create_user(email='flow1@example.com', password='pass12345', role='USER')
    client = _auth(user)

    proposal = Proposal.objects.create(name="P-ACT")
    # Optional: include a line to exercise copy path (not strictly required)
    ProposalLine.objects.create(parent=proposal, parent_ref_id=proposal.pk, status='OPEN',
                                item={"id_num": 1}, quantity={"ordered": 1}, price={"extended": 1})

    resp = client.post(f'/tx/proposals/{proposal.pk}/convert-to-sales-order/', {}, format='json')
    assert resp.status_code == 201  # type: ignore[attr-defined]
    body = resp.data  # type: ignore[attr-defined]
    payload = body.get('data') if isinstance(body, dict) else None
    assert isinstance(payload, dict)
    assert 'sales_order_id' in payload and 'order_no' in payload


@pytest.mark.django_db
def test_sales_order_to_invoice_action(django_user_model):
    # Permission for SalesOrder header
    Setting.objects.create(
        purpose='view_edit', model_name='sales_order', is_active=True,
        data={"USER": {"view": ["id"], "edit": ["id"]}}
    )
    user = django_user_model.objects.create_user(email='flow2@example.com', password='pass12345', role='USER')
    client = _auth(user)

    so = SalesOrder.objects.create(order_no="SO-T1")
    SalesOrderLine.objects.create(parent=so, parent_ref_id=so.pk, status='OPEN',
                                  price={"extended": 2}, cost={"extended": 1})

    resp = client.post(f'/tx/sales-orders/{so.pk}/convert-to-invoice/', {}, format='json')
    assert resp.status_code == 201  # type: ignore[attr-defined]
    body = resp.data  # type: ignore[attr-defined]
    payload = body.get('data') if isinstance(body, dict) else None
    assert isinstance(payload, dict)
    assert 'invoice_id' in payload and 'invoice_no' in payload


@pytest.mark.django_db
def test_receive_purchase_order_action(django_user_model):
    # Permission for PurchaseOrder header
    Setting.objects.create(
        purpose='view_edit', model_name='purchase_order', is_active=True,
        data={"USER": {"view": ["id"], "edit": ["id"]}}
    )
    user = django_user_model.objects.create_user(email='flow3@example.com', password='pass12345', role='USER')
    client = _auth(user)

    item = Item.objects.create(name='Widget', sku='W-1', description='Widget')
    wh = Warehouse.objects.create(code='MAIN', name='Main WH')
    po = PurchaseOrder.objects.create(po_no='PO-T1')
    pol = PurchaseOrderLine.objects.create(
        parent=po, parent_ref_id=po.pk, status='OPEN',
        item={"id_num": item.id}, cost={"unit": 12.34}
    )

    payload = {
        "receipt_no": "R-1001",
        "lines": [{"po_line_id": pol.id, "qty": "2.0", "warehouse_code": wh.code, "unit_cost": "11.11"}]
    }
    resp = client.post(f'/tx/purchase-orders/{po.pk}/receive/', payload, format='json')
    assert resp.status_code == 201  # type: ignore[attr-defined]
    body = resp.data  # type: ignore[attr-defined]
    payload = body.get('data') if isinstance(body, dict) else None
    assert isinstance(payload, dict)
    assert 'receipt_id' in payload and isinstance(payload.get('stacks_created'), list)
