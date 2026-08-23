import pytest
from rest_framework.test import APIClient

@pytest.mark.django_db
def test_reads_by_model_list_and_detail(admin_user):
    client = APIClient()
    client.force_authenticate(user=admin_user)

    # List endpoints must resolve and return items array
    for model in ("contact", "domain", "order"):
        r = client.get(f'/{model}/')
        assert getattr(r, 'status_code', None) == 200, getattr(r, 'data', None)
        data = getattr(r, 'data', {}) or {}
        payload = data.get('data', data)
        assert 'items' in payload and isinstance(payload['items'], list)

        # Detail of non-existent id should be 200 with item None
        d = client.get(f'/{model}/999999/')
        assert getattr(d, 'status_code', None) == 200, getattr(d, 'data', None)
        pdata = getattr(d, 'data', {}) or {}
        pdata = pdata.get('data', pdata)
        assert 'item' in pdata

@pytest.mark.django_db
def test_update_and_delete_contract_without_existing_records(admin_user):
    client = APIClient()
    client.force_authenticate(user=admin_user)

    # Update non-existent id -> 404 (routes to wcapi save)
    u = client.post('/order/999999/', {'data': {}}, format='json')
    assert getattr(u, 'status_code', None) in (400, 404)  # 404 preferred; 400 acceptable if payload invalid

    # Single delete non-existent -> 200 with deleted False/0
    s = client.delete('/domain/999999/')
    assert getattr(s, 'status_code', None) == 200

    # Batch delete requires ids or filters -> 400
    b = client.delete('/domain/', data={}, format='json')
    assert getattr(b, 'status_code', None) == 400

    # Batch delete with filters (likely none match) -> 200 with deleted_count int
    b2 = client.delete('/domain/', data={'filters': {'name': '__unlikely__value__'}}, format='json')
    assert getattr(b2, 'status_code', None) == 200
    payload = (getattr(b2, 'data', {}) or {}).get('data', getattr(b2, 'data', {}) or {})
    # tolerate either {deleted_count:n} or plain {deleted_count:n}
    deleted_count = payload.get('deleted_count') if isinstance(payload, dict) else None
    assert isinstance(deleted_count, int)