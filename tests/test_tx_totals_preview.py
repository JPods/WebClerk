import pytest
from rest_framework.test import APIClient

from apps.core.models.setting import Setting
from apps.transactions.models import (
    Proposal, ProposalLine,
    Order, OrderLine,
)
from .utils import assert_envelope


def _auth(user):
    from rest_framework_simplejwt.tokens import RefreshToken
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f'Bearer {RefreshToken.for_user(user).access_token}')
    return c


@pytest.mark.django_db
def test_preview_totals_scoped_to_kind(django_user_model):
    # Minimal permissions for headers so BasePermission passes
    for mn in ('proposal', 'order'):
        Setting.objects.create(purpose='view_edit', model_target=mn, is_active=True, data={"USER": {"view": ["id"], "edit": ["id"]}})

    user = django_user_model.objects.create_user(email='preview@example.com', password='pass12345', role='USER')
    client = _auth(user)

    # Create a proposal with two lines
    p = Proposal.objects.create(name='PX')
    ProposalLine.objects.create(parent=p, parent_ref_id=p.pk, price={"extended": "10.00"}, cost={"extended": "5.00"})
    ProposalLine.objects.create(parent=p, parent_ref_id=p.pk, price={"extended": "2.50"}, cost={"extended": "1.00"})

    # Also create a separate SO with a line to ensure scoping works
    so = Order.objects.create(order_no='SO-X')
    OrderLine.objects.create(parent=so, parent_ref_id=so.pk, price={"extended": "7.00"}, cost={"extended": "3.00"})

    r = client.get(f'/tx/proposal/{p.pk}/preview-totals/?include_breakdown=1')
    assert r.status_code == 200  # type: ignore[attr-defined]
    data = assert_envelope(getattr(r, 'data', {}), expect_status='success')
    assert data.get('parent_ref_id') == p.pk
    assert data.get('model') == 'proposal-line'
    # Totals only consider proposal lines
    assert data.get('total_lines') == 2
    assert data.get('total_price_extended') == '12.50'
    assert data.get('total_cost_extended') == '6.00'
    # Breakdown present when requested
    bk = data.get('breakdown') or {}
    assert 'proposal-line' in bk
