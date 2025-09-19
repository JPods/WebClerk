"""Transaction line aggregation & cross-model tests."""

from decimal import Decimal
import pytest
from rest_framework.test import APIClient
from apps.transactions.models import (
    Proposal, ProposalLine,
    SalesOrder, SalesOrderLine,
    Invoice, InvoiceLine,
    PurchaseOrder, PurchaseOrderLine,
    WorkOrder, WorkOrderLine,
    Requisition, RequisitionLine,
)
from apps.core.models.setting import Setting


def _auth(user):
    from rest_framework_simplejwt.tokens import RefreshToken
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f'Bearer {RefreshToken.for_user(user).access_token}')
    return c


@pytest.mark.django_db
def test_line_aggregation_simple(django_user_model):
    # Allow minimal view for aggregation auth (proposal_line & order_line)
    Setting.objects.create(purpose='view_edit', model_name='proposal_line', is_active=True,
                           data={"USER": {"view": ["id"], "edit": []}})
    Setting.objects.create(purpose='view_edit', model_name='sales_order_lines', is_active=True,
                           data={"USER": {"view": ["id"], "edit": []}})
    user = django_user_model.objects.create_user(email='agg@example.com', password='pass12345', role='USER')
    parent = Proposal.objects.create(name="P1")
    # Create two lines under the same parent with mixed numeric/string extended values
    ProposalLine.objects.create(parent=parent, parent_ref_id=parent.pk, status='OPEN',
                                price={"extended": "10.50"}, cost={"extended": 5})
    ProposalLine.objects.create(parent=parent, parent_ref_id=parent.pk, status='OPEN',
                                price={"extended": 2}, cost={"extended": "1.25"})
    client = _auth(user)
    resp = client.get(f'/tx/lines/aggregate/?parent_ref_id={parent.pk}')
    # Aggregator sums across all line models sharing the same parent_ref_id value (cross-document id collision allowed).
    assert resp.status_code == 200  # type: ignore[attr-defined]
    payload = resp.data  # type: ignore[attr-defined]
    # Envelope shape assertions
    assert payload.get('status') == 'success'
    assert 'data' in payload and isinstance(payload['data'], dict)
    data = payload['data']
    assert data['total_lines'] == 2
    assert Decimal(data['total_price_extended']) == Decimal('12.50')
    assert Decimal(data['total_cost_extended']) == Decimal('6.25')


@pytest.mark.django_db
def test_multi_model_permission_sales_order_line(django_user_model):
    Setting.objects.create(purpose='view_edit', model_name='sales_order_lines', is_active=True,
                           data={"USER": {"view": ["id", "status"], "edit": ["status"]}})
    user = django_user_model.objects.create_user(email='orderrole@example.com', password='pass12345', role='USER')
    parent = SalesOrder.objects.create(order_no="O2")
    SalesOrderLine.objects.create(parent=parent, parent_ref_id=parent.pk, status='OPEN')
    client = _auth(user)
    resp = client.get(f'/tx/sales-order-lines/?parent_ref_id={parent.pk}')
    assert resp.status_code == 200  # type: ignore[attr-defined]
    payload = resp.data  # type: ignore[attr-defined]
    item = payload['data']['results'][0]
    assert 'status' in item


@pytest.mark.django_db
def test_public_fallback(django_user_model):
    # No USER key; should fallback to PUBLIC
    Setting.objects.create(purpose='view_edit', model_name='proposal_line', is_active=True,
                           data={"PUBLIC": {"view": ["id", "status"], "edit": []}})
    user = django_user_model.objects.create_user(email='pub@example.com', password='pass12345', role='USER')
    parent = Proposal.objects.create(name="P2")
    ProposalLine.objects.create(parent=parent, parent_ref_id=parent.pk, status='OPEN')
    client = _auth(user)
    resp = client.get(f'/tx/proposal-lines/?parent_ref_id={parent.pk}')
    assert resp.status_code == 200  # type: ignore[attr-defined]
    payload = resp.data  # type: ignore[attr-defined]
    item = payload['data']['results'][0]
    assert 'status' in item

@pytest.mark.django_db
def test_scoped_aggregation(django_user_model):
    Setting.objects.create(purpose='view_edit', model_name='proposal_line', is_active=True,
                           data={"USER": {"view": ["id"], "edit": []}})
    Setting.objects.create(purpose='view_edit', model_name='invoice_line', is_active=True,
                           data={"USER": {"view": ["id"], "edit": []}})
    user = django_user_model.objects.create_user(email='scope@example.com', password='pass12345', role='USER')
    parent = Proposal.objects.create(name="P3")
    inv_parent = Invoice.objects.create()
    ProposalLine.objects.create(parent=parent, parent_ref_id=parent.pk, status='OPEN', price={'extended': '3'}, cost={'extended': '1'})
    InvoiceLine.objects.create(parent=inv_parent, parent_ref_id=inv_parent.pk, status='OPEN', price={'extended': '7'}, cost={'extended': '2'})
    client = _auth(user)
    # Unscoped will sum both if parent_ref_ids collide; ensure different IDs first
    resp_scoped = client.get(f'/tx/lines/aggregate/?parent_ref_id={parent.pk}&model=proposal-line')
    assert resp_scoped.status_code == 200  # type: ignore[attr-defined]
    scoped_payload = resp_scoped.data  # type: ignore[attr-defined]
    assert scoped_payload.get('status') == 'success'
    assert 'data' in scoped_payload
    scoped = scoped_payload['data']
    assert scoped['total_lines'] == 1 and scoped['total_price_extended'] == '3'


@pytest.mark.django_db
def test_permissions_remaining_line_models(django_user_model):
    # Create minimal PUBLIC rule for all remaining models
    models_tables = ['invoice_line','purchase_order_lines','work_order_lines','requisition_line']
    for tbl in models_tables:
        Setting.objects.create(purpose='view_edit', model_name=tbl, is_active=True,
                               data={"PUBLIC": {"view": ["id", "status"], "edit": []}})
    user = django_user_model.objects.create_user(email='puball@example.com', password='pass12345', role='GUEST')
    inv = Invoice.objects.create()
    pur = PurchaseOrder.objects.create(po_no='P1')
    wo = WorkOrder.objects.create(work_no='W1')
    req = Requisition.objects.create(req_no='R1')
    InvoiceLine.objects.create(parent=inv, parent_ref_id=inv.pk, status='SENT')
    PurchaseOrderLine.objects.create(parent=pur, parent_ref_id=pur.pk, status='OPEN')
    WorkOrderLine.objects.create(parent=wo, parent_ref_id=wo.pk, status='OPEN')
    RequisitionLine.objects.create(parent=req, parent_ref_id=req.pk, status='OPEN')
    client = _auth(user)
    for endpoint in ['invoice-lines','purchase-order-lines','workorder-lines','requisition-lines']:
        pid = {'invoice-lines': inv.pk, 'purchase-order-lines': pur.pk, 'workorder-lines': wo.pk, 'requisition-lines': req.pk}[endpoint]
        resp = client.get(f'/tx/{endpoint}/?parent_ref_id={pid}')
        assert resp.status_code == 200  # type: ignore[attr-defined]
        payload = resp.data  # type: ignore[attr-defined]
        item = payload['data']['results'][0]
        assert 'status' in item


@pytest.mark.django_db
def test_negative_edit_error_detail(django_user_model):
    # USER can edit only status
    Setting.objects.create(purpose='view_edit', model_name='proposal_line', is_active=True,
                           data={"USER": {"view": ["id","status","probability"], "edit": ["status"]}})
    user = django_user_model.objects.create_user(email='neg@example.com', password='pass12345', role='USER')
    parent = Proposal.objects.create(name='NP')
    line = ProposalLine.objects.create(parent=parent, parent_ref_id=parent.pk, status='OPEN', probability=50)
    client = _auth(user)
    resp = client.patch(f'/tx/proposal-lines/{line.pk}/', {"status": "CLOSED", "probability": 10}, format='json')
    # Expect 400 with per-field errors for probability only
    assert resp.status_code == 400  # type: ignore[attr-defined]
    payload = resp.data  # type: ignore[attr-defined]
    assert payload.get('status') == 'fail'
    assert 'error' in payload and payload['error'].get('code') == 'validation_error'
    # DRF serializer errors exposed under error.details
    details = payload['error'].get('details') or {}
    # Expect probability field message list
    assert 'probability' in details
    prob_msgs = details['probability']
    assert isinstance(prob_msgs, list) and any('Not editable for role' in m for m in prob_msgs)


@pytest.mark.django_db
def test_aggregation_invalid_model(django_user_model):
    Setting.objects.create(purpose='view_edit', model_name='proposal_line', is_active=True,
                           data={"USER": {"view": ["id"], "edit": []}})
    user = django_user_model.objects.create_user(email='badagg@example.com', password='pass12345', role='USER')
    parent = Proposal.objects.create(name='BadAgg')
    ProposalLine.objects.create(parent=parent, parent_ref_id=parent.pk, status='OPEN')
    client = _auth(user)
    resp = client.get(f'/tx/lines/aggregate/?parent_ref_id={parent.pk}&model=not-a-model')
    assert resp.status_code == 400  # type: ignore[attr-defined]
    assert 'data' in resp.data and 'detail' in resp.data['data']  # type: ignore[attr-defined]


@pytest.mark.django_db
def test_unscoped_aggregation_breakdown(django_user_model):
    for tbl in ['proposal_line','sales_order_lines']:
        Setting.objects.create(
            purpose='view_edit',
            model_name=tbl,
            is_active=True,
            data={"USER": {"view": ["id"], "edit": []}}
        )
    user = django_user_model.objects.create_user(email='breakdown@example.com', password='pass12345', role='USER')
    proposal = Proposal.objects.create(name='BD')
    order = SalesOrder.objects.create(order_no='BD1')
    ProposalLine.objects.create(parent=proposal, parent_ref_id=proposal.pk, status='OPEN', price={'extended':'2'}, cost={'extended':'1'})
    SalesOrderLine.objects.create(parent=order, parent_ref_id=order.pk, status='OPEN', price={'extended':'3'}, cost={'extended':'2'})
    client = _auth(user)
    # Use proposal parent_ref_id so only proposal line counts; breakdown should reflect just that model
    resp = client.get(f'/tx/lines/aggregate/?parent_ref_id={proposal.pk}')
    assert resp.status_code == 200  # type: ignore[attr-defined]
    data = resp.data  # type: ignore[attr-defined]
    assert 'breakdown' in data['data']
    assert 'proposal-line' in data['data']['breakdown']
    assert data['data']['breakdown']['proposal-line']['price_extended'] == '2'


@pytest.mark.django_db
def test_scoped_aggregation_with_breakdown_and_ttl_override(django_user_model):
    Setting.objects.create(purpose='view_edit', model_name='proposal_line', is_active=True,
                           data={"USER": {"view": ["id"], "edit": []}})
    user = django_user_model.objects.create_user(email='scopedbd@example.com', password='pass12345', role='USER')
    proposal = Proposal.objects.create(name='SBD')
    ProposalLine.objects.create(parent=proposal, parent_ref_id=proposal.pk, status='OPEN', price={'extended':'5'}, cost={'extended':'2'})
    client = _auth(user)
    resp = client.get(f'/tx/lines/aggregate/?parent_ref_id={proposal.pk}&model=proposal-line&include_breakdown=1&ttl=15')
    assert resp.status_code == 200  # type: ignore[attr-defined]
    data = resp.data  # type: ignore[attr-defined]
    assert data['data']['model'] == 'proposal-line'
    assert 'breakdown' in data['data'] and 'proposal-line' in data['data']['breakdown']
    assert data['data']['ttl_seconds'] == 15



@pytest.mark.django_db
def test_field_auth_matrix_batch(django_user_model):
    Setting.objects.create(purpose='view_edit', model_name='proposal_line', is_active=True,
                           data={"USER": {"view": ["id","status"], "edit": ["status"]}})
    Setting.objects.create(purpose='view_edit', model_name='sales_order_lines', is_active=True,
                           data={"USER": {"view": ["id"], "edit": []}})
    user = django_user_model.objects.create_user(email='batch@example.com', password='pass12345', role='USER')
    client = _auth(user)
    resp = client.get('/tx/auth/fields/batch/?models=proposal-line,sales-order-line,missing-line')
    assert resp.status_code == 200  # type: ignore[attr-defined]
    data = resp.data  # type: ignore[attr-defined]
    models_block = data['data']['models']
    assert 'proposal-line' in models_block and 'sales-order-line' in models_block
    assert models_block['missing-line']['error'] == 'invalid-model'

@pytest.mark.django_db
def test_field_auth_matrix_batch_post(django_user_model):
    Setting.objects.create(purpose='view_edit', model_name='proposal_line', is_active=True,
                           data={"USER": {"view": ["id","status"], "edit": ["status"]}})
    user = django_user_model.objects.create_user(email='batchpost@example.com', password='pass12345', role='USER')
    client = _auth(user)
    resp = client.post('/tx/auth/fields/batch/', {"models": ["proposal-line", "missing-line"]}, format='json')
    assert resp.status_code == 200  # type: ignore[attr-defined]
    data = resp.data  # type: ignore[attr-defined]
    models_block = data['data']['models']
    assert 'proposal-line' in models_block and models_block['missing-line']['error'] == 'invalid-model'
