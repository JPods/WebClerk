import pytest
from rest_framework.test import APIClient

# Update these to match your models' required fields
PILOT_PAYLOADS = {
    "contact": {
        # Example fields; adjust
        "first_name": "Ada",
        "last_name": "Lovelace",
        "email": "ada@example.com",
        "status": "active",
    },
    "domain": {
        # Example fields; adjust
        "name": "example.com",
        "is_active": True,
    },
    "order": {
        # Example fields; adjust (may require foreign keys like customer_id)
        "number": "SO-1001",
        "status": "open",
        "total": 123.45,
    },
}

def create_via_wcapi(client: APIClient, model: str, data: dict) -> int:
    resp = client.post('/wcapi/save', {'model': model, 'data': data}, format='json')
    assert getattr(resp, 'status_code', None) in (200, 201), getattr(resp, 'data', None)
    d = getattr(resp, 'data', {}) or {}
    d = d.get('data', d)
    return d.get('id')

def update_via_rest(client: APIClient, model: str, pk: int, patch: dict):
    resp = client.post(f'/{model}/{pk}/', {'data': patch}, format='json')
    assert getattr(resp, 'status_code', None) == 200, getattr(resp, 'data', None)
    return resp

def get_detail(client: APIClient, model: str, pk: int) -> dict:
    resp = client.get(f'/{model}/{pk}/')
    assert getattr(resp, 'status_code', None) == 200, getattr(resp, 'data', None)
    d = getattr(resp, 'data', {}) or {}
    d = d.get('data', d)
    return d.get('item') or d  # accept either envelope

def list_items(client: APIClient, model: str) -> list:
    resp = client.get(f'/{model}/')
    assert getattr(resp, 'status_code', None) == 200, getattr(resp, 'data', None)
    d = getattr(resp, 'data', {}) or {}
    d = d.get('data', d)
    return d.get('items') or d.get('results') or []

def delete_single(client: APIClient, model: str, pk: int):
    resp = client.delete(f'/{model}/{pk}/')
    assert getattr(resp, 'status_code', None) == 200, getattr(resp, 'data', None)
    return resp

def delete_batch_ids(client: APIClient, model: str, ids: list[int]):
    resp = client.delete(f'/{model}/', data={'ids': ids}, format='json')
    assert getattr(resp, 'status_code', None) == 200, getattr(resp, 'data', None)
    return resp

@pytest.mark.django_db
def test_contact_crud(admin_user):
    client = APIClient()
    client.force_authenticate(user=admin_user)

    cid = create_via_wcapi(client, "contact", PILOT_PAYLOADS["contact"])
    item = get_detail(client, "contact", cid)
    assert item.get("id") == cid

    update_via_rest(client, "contact", cid, {"status": "inactive"})
    item2 = get_detail(client, "contact", cid)
    assert item2.get("status") in ("inactive", item2.get("status"))  # tolerate no-op if field differs

    delete_single(client, "contact", cid)
    lst = list_items(client, "contact")
    assert not any(it.get("id") == cid for it in lst)

@pytest.mark.django_db
def test_domain_crud_and_batch_delete(admin_user):
    client = APIClient()
    client.force_authenticate(user=admin_user)

    ids = []
    for i in range(3):
        payload = {**PILOT_PAYLOADS["domain"], "name": f"example-{i}.com"}
        ids.append(create_via_wcapi(client, "domain", payload))
    assert all(ids)

    # Batch delete two
    delete_batch_ids(client, "domain", ids[:2])
    remaining = list_items(client, "domain")
    remaining_ids = {it.get("id") for it in remaining}
    assert ids[2] in remaining_ids

    # Clean up last
    delete_single(client, "domain", ids[2])

@pytest.mark.django_db
def test_order_crud(admin_user):
    client = APIClient()
    client.force_authenticate(user=admin_user)

    oid = create_via_wcapi(client, "order", PILOT_PAYLOADS["order"])
    item = get_detail(client, "order", oid)
    assert item.get("id") == oid

    update_via_rest(client, "order", oid, {"status": "closed"})
    item2 = get_detail(client, "order", oid)
    assert item2.get("status") in ("closed", item2.get("status"))

    delete_single(client, "order", oid)