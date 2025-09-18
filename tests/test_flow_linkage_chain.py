import pytest
from rest_framework.test import APIClient
from apps.core.models.setting import Setting
from apps.transactions.models import Proposal, ProposalLine, SalesOrderLine, SalesOrder, InvoiceLine, Invoice, PurchaseOrderLine, PurchaseOrder


def _auth(user):
    from rest_framework_simplejwt.tokens import RefreshToken
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f'Bearer {RefreshToken.for_user(user).access_token}')
    return c

@pytest.mark.django_db
def test_linkage_propagation_proposal_order_invoice_po(django_user_model):
    # Minimal permissions for involved models
    for model in ('proposal', 'sales_order', 'invoice', 'purchase_order'):
        Setting.objects.create(purpose='view_edit', model_name=model, is_active=True, data={'USER': {'view': ['id'], 'edit': ['id']}})
    user = django_user_model.objects.create_user(email='linkage1@example.com', password='pass12345', role='USER')
    client = _auth(user)

    proposal = Proposal.objects.create(name='LNK-PROP')
    pl = ProposalLine.objects.create(parent=proposal, parent_ref_id=proposal.pk, status='OPEN', comments={'public':'from proposal'}, price={'extended':1})

    # Convert proposal -> sales order
    resp1 = client.post(f'/tx/proposals/{proposal.pk}/convert-to-sales-order/', {}, format='json')
    assert resp1.status_code == 201  # type: ignore[attr-defined]

    so_id = resp1.data['data']['sales_order_id']  # type: ignore[attr-defined]
    so = SalesOrder.objects.get(pk=so_id)
    sol = SalesOrderLine.objects.filter(parent=so).first()
    assert sol is not None
    # Linkage id should now exist
    linkage_ids = (sol.refs or {}).get('links', {}).get('linkage', []) if sol.refs else []
    assert linkage_ids and isinstance(linkage_ids, list)
    linkage_id = linkage_ids[0]

    # Convert sales order -> invoice
    resp2 = client.post(f'/tx/sales-orders/{so_id}/convert-to-invoice/', {}, format='json')
    assert resp2.status_code == 201  # type: ignore[attr-defined]
    inv_id = resp2.data['data']['invoice_id']  # type: ignore[attr-defined]
    inv = Invoice.objects.get(pk=inv_id)
    il = InvoiceLine.objects.filter(parent=inv).first()
    assert il is not None
    inv_linkage_ids = (il.refs or {}).get('links', {}).get('linkage', []) if il.refs else []
    assert inv_linkage_ids and inv_linkage_ids[0] == linkage_id

    # Also convert sales order -> purchase order
    resp3 = client.post(f'/tx/sales-orders/{so_id}/convert-to-purchase-order/', {}, format='json')
    assert resp3.status_code == 201  # type: ignore[attr-defined]
    po_id = resp3.data['data']['purchase_order_id']  # type: ignore[attr-defined]
    po = PurchaseOrder.objects.get(pk=po_id)
    pol = PurchaseOrderLine.objects.filter(parent=po).first()
    assert pol is not None
    po_linkage_ids = (pol.refs or {}).get('links', {}).get('linkage', []) if pol.refs else []
    assert po_linkage_ids and po_linkage_ids[0] == linkage_id

    # Comments aggregation endpoint (should gather at least the original proposal line public comment)
    resp4 = client.get(f'/tx/linkages/{linkage_id}/comments/')
    assert resp4.status_code == 200  # type: ignore[attr-defined]
    items = resp4.data['data']['items']  # type: ignore[attr-defined]
    assert any(it.get('comments', {}).get('public') == 'from proposal' for it in items)
    comments_root = resp4.data['data']['comments']  # type: ignore[attr-defined]
    assert 'general' in comments_root and 'public' in comments_root['general']
