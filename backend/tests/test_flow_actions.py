import pytest

from apps.core.models.setting import Setting
from apps.transactions.models import (
    Quote, QuoteLine,
    Order, OrderLine,
    Purchase, PurchaseLine,
)
from apps.products.models.item import Item
from apps.products.models.warehouse import Warehouse


def _permission_setting(parent_model, config):
    """Minimal wc:view_edit rule; new Setting records require explicit authorization."""
    rule = Setting(purpose='wc:view_edit', parent_model=parent_model, is_active=True, config=config)
    rule._setting_create_authorized = True
    rule.save()
    return rule


def _auth(user):
    from tests.helpers.auth import make_authenticated_client
    return make_authenticated_client(user)


@pytest.mark.django_db
def test_quote_to_order_action(django_user_model):
    # Minimal permission rules for Quote (header) actions
    _permission_setting('quote', {"USER": {"view": ["id"], "edit": ["id"]}})
    user = django_user_model.objects.create_user(email='flow1@example.com', password='pass12345', role='USER')
    client = _auth(user)

    quote = Quote.objects.create(name="P-ACT")
    # Optional: include a line to exercise copy path (not strictly required)
    QuoteLine.objects.create(quote=quote, status='OPEN',
                                item={"id_num": 1}, quantity={"active": 1}, price={"extended": 1})

    resp = client.post(f'/wcapi/quote/{quote.pk}/convert-to-order/', {}, format='json')
    assert resp.status_code == 201  # type: ignore[attr-defined]
    body = resp.data  # type: ignore[attr-defined]
    payload = body.get('data') if isinstance(body, dict) else None
    assert isinstance(payload, dict)
    assert 'order_id' in payload


@pytest.mark.django_db
def test_order_to_invoice_action(django_user_model):
    # Permission for Order header
    _permission_setting('order', {"USER": {"view": ["id"], "edit": ["id"]}})
    user = django_user_model.objects.create_user(email='flow2@example.com', password='pass12345', role='USER')
    client = _auth(user)

    so = Order.objects.create(ida="SO-T1")
    OrderLine.objects.create(order=so, status='OPEN',
                                  price={"extended": 2}, cost={"extended": 1})

    resp = client.post(f'/wcapi/order/{so.pk}/convert-to-invoice/', {}, format='json')
    assert resp.status_code == 201  # type: ignore[attr-defined]
    body = resp.data  # type: ignore[attr-defined]
    payload = body.get('data') if isinstance(body, dict) else None
    assert isinstance(payload, dict)
    assert 'invoice_id' in payload


@pytest.mark.django_db
def test_receive_purchase_action(django_user_model):
    # Permission for Purchase header
    _permission_setting('purchase', {"USER": {"view": ["id"], "edit": ["id"]}})
    user = django_user_model.objects.create_user(email='flow3@example.com', password='pass12345', role='USER')
    client = _auth(user)

    item = Item.objects.create(name='Widget', sku='W-1', description='Widget')
    wh = Warehouse.objects.create(code='MAIN', name='Main WH')
    po = Purchase.objects.create(ida='PO-T1')
    pol = PurchaseLine.objects.create(
        purchase=po, status='OPEN',
        item={"id_num": item.id}, cost={"unit": 12.34}
    )

    payload = {
        "receipt_id": "R-1001",
        "lines": [{"po_line_id": pol.id, "qty": "2.0", "warehouse_code": wh.code, "unit_cost": "11.11"}]
    }
    resp = client.post(f'/wcapi/purchase/{po.pk}/receive-goods/', payload, format='json')
    assert resp.status_code in (200, 201)  # type: ignore[attr-defined]
    body = resp.data  # type: ignore[attr-defined]
    # Response may wrap in 'data' or return directly
    result = body.get('data', body) if isinstance(body, dict) else body
    assert isinstance(result, dict)
