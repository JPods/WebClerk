import pytest
from rest_framework.test import APIClient
from apps.core.models.setting import Setting
from apps.transactions.models import Quote, QuoteLine, OrderLine, Order, InvoiceLine, Invoice, PurchaseLine, Purchase
from tests.conftest import make_setting


def _auth(user):
    from rest_framework_simplejwt.tokens import RefreshToken
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f'Bearer {RefreshToken.for_user(user).access_token}')
    return c

@pytest.mark.django_db
@pytest.mark.skip(reason="Linkage tracking and /linkages/ endpoint not yet implemented")
def test_linkage_propagation_quote_order_invoice_po(django_user_model):
    # Minimal permissions for involved models
    for model in ('quote', 'order', 'invoice', 'purchase'):
        make_setting(purpose='wc:view_edit', parent_model=model, is_active=True, config={'USER': {'view': ['id'], 'edit': ['id']}})
    user = django_user_model.objects.create_user(email='linkage1@example.com', password='pass12345', role='USER')
    client = _auth(user)

    quote = Quote.objects.create(name='LNK-PROP')
    pl = QuoteLine.objects.create(quote=quote, status='OPEN', comments={'public':'from quote'}, price={'extended':1})

    # Convert quote -> sales order
    resp1 = client.post(f'/wcapi/quote/{quote.pk}/convert-to-order/', {}, format='json')
    assert resp1.status_code == 201  # type: ignore[attr-defined]

    so_id = resp1.data['data']['order_id']  # type: ignore[attr-defined]
    so = Order.objects.get(pk=so_id)
    sol = OrderLine.objects.filter(order=so).first()
    assert sol is not None
    # Linkage id should now exist
    linkage_ids = (sol.refs or {}).get('links', {}).get('linkage', []) if sol.refs else []
    assert linkage_ids and isinstance(linkage_ids, list)
    linkage_id = linkage_ids[0]

    # Convert sales order -> invoice
    resp2 = client.post(f'/wcapi/order/{so_id}/convert-to-invoice/', {}, format='json')
    assert resp2.status_code == 201  # type: ignore[attr-defined]
    inv_id = resp2.data['data']['invoice_id']  # type: ignore[attr-defined]
    inv = Invoice.objects.get(pk=inv_id)
    il = InvoiceLine.objects.filter(invoice=inv).first()
    assert il is not None
    inv_linkage_ids = (il.refs or {}).get('links', {}).get('linkage', []) if il.refs else []
    assert inv_linkage_ids and inv_linkage_ids[0] == linkage_id

    # Also convert sales order -> purchase order
    resp3 = client.post(f'/wcapi/order/{so_id}/convert-to-purchase/', {}, format='json')
    assert resp3.status_code == 201  # type: ignore[attr-defined]
    po_id = resp3.data['data']['purchase_id']  # type: ignore[attr-defined]
    po = Purchase.objects.get(pk=po_id)
    pol = PurchaseLine.objects.filter(purchase=po).first()
    assert pol is not None
    po_linkage_ids = (pol.refs or {}).get('links', {}).get('linkage', []) if pol.refs else []
    assert po_linkage_ids and po_linkage_ids[0] == linkage_id

    # Comments aggregation endpoint (should gather at least the original quote line public comment)
    resp4 = client.get(f'/wcapi/linkages/{linkage_id}/comments/')
    assert resp4.status_code == 200  # type: ignore[attr-defined]
    items = resp4.data['data']['items']  # type: ignore[attr-defined]
    assert any(it.get('comments', {}).get('public') == 'from quote' for it in items)
    comments_root = resp4.data['data']['comments']  # type: ignore[attr-defined]
    assert 'general' in comments_root and 'public' in comments_root['general']
