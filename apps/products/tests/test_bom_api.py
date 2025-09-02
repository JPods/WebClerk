import pytest
from django.urls import reverse
from apps.products.models.item import Item
from apps.products.models.bom import BillOfMaterial
from django.contrib.auth import get_user_model
from apps.core.models.contact import Contact


@pytest.mark.django_db
def test_bom_list_create(client):
    User = get_user_model()
    # Custom user model uses email as USERNAME_FIELD and requires name_first/name_last
    user = Contact.objects.create(email='bomtester@example.com', name_first='Bo', name_last='M')
    user.set_password('pass')
    user.save()
    client.force_login(user)
    parent = Item.objects.create(name='Parent Widget')
    component = Item.objects.create(name='Component Screw')
    url = reverse('products:bom-list-create', args=[parent.id])
    # list empty
    resp = client.get(url)
    assert resp.status_code == 200
    body = resp.json()
    assert body['status'] == 'success'
    assert body['data'] == []
    # create
    payload = {
        'component_id': component.id,
        'quantity': '2',
        'scrap_factor': '0',
        'sequence': 10
    }
    resp = client.post(url, payload)
    assert resp.status_code == 201, resp.content
    created = resp.json()['data']
    assert created['parent'] == parent.id
    assert created['component'] == component.id
    # list again
    resp = client.get(url)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body['data']) == 1
    # Raw mode deprecated: ?raw=1 still returns enveloped structure
    raw_resp = client.get(url + '?raw=1')
    raw_body = raw_resp.json()
    assert raw_body.get('status') == 'success' and isinstance(raw_body.get('data'), list)
