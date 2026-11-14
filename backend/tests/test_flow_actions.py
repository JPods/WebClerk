import pytest

from apps.core.models.setting import Setting
from apps.transactions.models import (
    Quote, QuoteLine,
    Order, OrderLine,
    Purchase, PurchaseLine,
)
from apps.products.models.item import Item
from apps.products.models.warehouse import Warehouse
import secrets

# Generated per run — no password literal in the repository.
TEST_PASSWORD = secrets.token_urlsafe(16)




def _party(kind):
    """A complete document names its party and terms, or the money steps refuse it (the team, 2026-11-06)."""
    from apps.accounts.models import Term
    from apps.orgs.models import Customer, Vendor
    Term.objects.get_or_create(ida='N30', defaults={'name': 'N30', 'is_active': True})
    return (Customer if kind == 'customer' else Vendor).objects.create(company=f'Flow {kind}').pk
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
    user = django_user_model.objects.create_user(email='flow1@example.com', password=TEST_PASSWORD, role='admin')
    client = _auth(user)

    quote = Quote.objects.create(name="P-ACT", customer_id=_party("customer"), terms="N30")
    # Optional: include a line to exercise copy path (not strictly required)
    QuoteLine.objects.create(quote=quote, status='OPEN',
                                item={"id_num": 1}, quantity={"active": 1}, price={"amount": 1})

    resp = client.post(f'/wcapi/quote/{quote.pk}/convert/', {'to': 'order'}, format='json')
    assert resp.status_code == 200, resp.content  # type: ignore[attr-defined]
    result = resp.json()['data']['result']
    assert Order.objects.get(pk=result['order_id']).parent_id == quote.pk


@pytest.mark.django_db
def test_order_to_invoice_action(django_user_model):
    # Permission for Order header
    _permission_setting('order', {"USER": {"view": ["id"], "edit": ["id"]}})
    user = django_user_model.objects.create_user(email='flow2@example.com', password=TEST_PASSWORD, role='admin')
    client = _auth(user)

    so = Order.objects.create(ida="SO-T1", customer_id=_party("customer"), terms="N30")
    # A line with a quantity to invoice: the one engine refuses a line with nothing left
    # (the old hand-built invoice accepted it and made a zero-quantity invoice).
    OrderLine.objects.create(order=so, status='OPEN', quantity={"active": 1},
                                  price={"amount": 2}, cost={"extended": 1})

    resp = client.post(f'/wcapi/order/{so.pk}/convert/', {'to': 'invoice'}, format='json')
    assert resp.status_code == 200, resp.content  # type: ignore[attr-defined]
    result = resp.json()['data']['result']
    # Convert makes the parent; its first save posts the proposed lines (Bill, 2026-11-13).
    assert 'invoice_id' in result and 'lines_saved' not in result
    proposed = client.post(f"/wcapi/invoice/{result['invoice_id']}/propose/", {}, format='json')
    lines = proposed.json()['data']['result']['lines']
    assert len(lines) == 1
    saved = client.put(f"/wcapi/invoice/{result['invoice_id']}/",
                       {'lines': [{'_from': lines[0]['_from']}]}, format='json')
    assert saved.status_code == 200, saved.content  # type: ignore[attr-defined]
    from apps.transactions.models import InvoiceLine
    assert InvoiceLine.objects.filter(invoice_id=result['invoice_id']).count() == 1


@pytest.mark.django_db
def test_receive_purchase_action(django_user_model):
    # Permission for Purchase header
    _permission_setting('purchase', {"USER": {"view": ["id"], "edit": ["id"]}})
    user = django_user_model.objects.create_user(email='flow3@example.com', password=TEST_PASSWORD, role='admin')
    client = _auth(user)

    item = Item.objects.create(name='Widget', sku='W-1', description='Widget')
    Warehouse.objects.create(code='MAIN', name='Main WH')
    po = Purchase.objects.create(ida='PO-T1', vendor_id=_party('vendor'), terms='N30')
    pol = PurchaseLine.objects.create(
        purchase=po, status='OPEN', item_fk=item,
        item={"item_id": item.id}, quantity={"active": 2, "staged": 2}, cost={"unit": 12.34}
    )

    resp = client.post(f'/wcapi/purchase/{po.pk}/convert/', {"to": "receipt"}, format='json')
    assert resp.status_code == 200, resp.content  # type: ignore[attr-defined]
    result = resp.json()['data']['result']
    # Convert makes the parent; the first save names the lines and receives (Bill, 2026-11-13).
    assert result['receipt_ida'] and 'lines' not in result
    saved = client.put(f"/wcapi/receipt/{result['receipt_id']}/",
                       {'lines': [{'_from': pol.id, 'quantity': {'active': "2.0"}}]}, format='json')
    assert saved.status_code == 200, saved.content  # type: ignore[attr-defined]
