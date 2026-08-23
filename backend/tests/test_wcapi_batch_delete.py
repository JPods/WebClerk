import pytest
from rest_framework.test import APIClient

@pytest.mark.django_db
def test_batch_delete_by_ids(admin_user):
    client = APIClient()
    client.force_authenticate(user=admin_user)

    payload = {
        'situation': 'Cleanup batch ids',
        'objective': {'summary': 'x', 'success': {'definition': 'ok', 'metrics': []}},
        'priority': 1, 'status': 'active', 'attention': 'low', 'intent': 'test', 'category': 'batch_ids'
    }

    ids = []
    for i in range(3):
        resp = client.post('/wcapi/save', {'model': 'project', 'data': {**payload, 'intent': f'test-{i}'}}, format='json')
        assert getattr(resp, 'status_code', 0) in (200, 201), getattr(resp, 'data', None)
        body = getattr(resp, 'data', {}) or {}
        body = body.get('data', body)
        ids.append(body.get('id'))
    assert all(ids)

    # Delete two by ids
    del_resp = client.delete('/project/', data={'ids': ids[:2]}, format='json')
    assert getattr(del_resp, 'status_code', 0) == 200, getattr(del_resp, 'data', None)
    deleted_count = (del_resp.data or {}).get('deleted_count')  # type: ignore[attr-defined]
    assert deleted_count == 2

    # Ensure last one still exists
    get_one = client.get(f'/project/{ids[2]}/')
    assert getattr(get_one, 'status_code', 0) == 200
    data = getattr(get_one, 'data', {}) or {}
    data = data.get('data', data)
    assert (data.get('item') or {}).get('id') == ids[2]

@pytest.mark.django_db
def test_batch_delete_by_filters(admin_user):
    client = APIClient()
    client.force_authenticate(user=admin_user)

    # Create targets with unique category to filter
    payload = {
        'situation': 'Cleanup batch filters',
        'objective': {'summary': 'x', 'success': {'definition': 'ok', 'metrics': []}},
        'priority': 1, 'status': 'active', 'attention': 'low', 'intent': 'test', 'category': 'batch_filter_tag'
    }
    for i in range(4):
        resp = client.post('/wcapi/save', {'model': 'project', 'data': {**payload, 'intent': f'flt-{i}'}}, format='json')
        assert getattr(resp, 'status_code', 0) in (200, 201)

    # Verify they exist via query
    q = client.post('/wcapi/query', {'model': 'project', 'filters': {'category': 'batch_filter_tag'}}, format='json')
    assert getattr(q, 'status_code', 0) == 200
    qdata = getattr(q, 'data', {}) or {}
    qdata = qdata.get('data', qdata)
    items = qdata.get('items') or []
    assert len(items) >= 4

    # Batch delete by filters on canonical route
    del_resp = client.delete('/project/', data={'filters': {'category': 'batch_filter_tag'}}, format='json')
    assert getattr(del_resp, 'status_code', 0) == 200
    deleted_count = ((del_resp.data or {}).get('deleted_count') or 0)  # type: ignore[attr-defined]
    assert deleted_count >= 4

    # Confirm none remain
    q2 = client.post('/wcapi/query', {'model': 'project', 'filters': {'category': 'batch_filter_tag'}}, format='json')
    q2data = getattr(q2, 'data', {}) or {}
    q2data = q2data.get('data', q2data)
    assert (q2data.get('items') or []) == []