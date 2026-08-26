import pytest
from apps.products.models.item import Item
from apps.products.models.bill_of_material import BillOfMaterial
from apps.core.models.contact import Contact
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_bom_list_via_wcapi():
    """Test that BOM records can be listed via /wcapi/get/."""
    user = Contact.objects.create(email='bomtester@example.com', name_first='Bo', name_last='M', is_staff=True)
    client = APIClient()
    client.force_authenticate(user=user)
    client.defaults['HTTP_ACCEPT'] = 'application/json'
    client.defaults['HTTP_X_REQUESTED_WITH'] = 'XMLHttpRequest'

    # List via wcapi/get/ with correct model key (GET only, no POST)
    resp = client.get('/wcapi/get/', {'model_name': 'bill_of_material'})
    assert resp.status_code == 200, f"Unexpected: {resp.status_code} {resp.content}"
    body = resp.json()
    assert body.get('status') == 'success'


@pytest.mark.django_db
def test_bom_create_via_wcapi():
    """Test that BOM records can be created via /wcapi/save/."""
    user = Contact.objects.create(email='bomcreator@example.com', name_first='Bo', name_last='C', is_staff=True)
    client = APIClient()
    client.force_authenticate(user=user)
    client.defaults['HTTP_ACCEPT'] = 'application/json'
    client.defaults['HTTP_X_REQUESTED_WITH'] = 'XMLHttpRequest'

    parent = Item.objects.create(name='Parent Widget')
    component = Item.objects.create(name='Component Screw')

    payload = {
        'model_name': 'bill_of_material',
        'data': {
            'parent_item_id': parent.id,
            'child_item_id': component.id,
            'quantity': '2',
            'scrap_factor': '0',
            'sequence': 10,
        }
    }
    resp = client.post('/wcapi/save/', payload, format='json')
    assert resp.status_code in (200, 201), f"Unexpected: {resp.status_code} {resp.content}"
    body = resp.json()
    assert body.get('status') == 'success'
