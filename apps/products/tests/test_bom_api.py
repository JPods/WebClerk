import pytest
from django.urls import reverse
from apps.products.models.item import Item
from apps.products.models.bill_of_material import BillOfMaterial
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
    url = '/domain/'
    # list empty
    resp = client.get(url)
    assert resp.status_code == 200
    body = resp.json()
    assert body['status'] == 'success'
    assert isinstance(body['data'], dict)
    assert body['data'].get('results') == []
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
    assert len(body['data'].get('results', [])) == 1
    # Raw query parameter is ignored; responses remain enveloped
    raw_resp = client.get(url + '?raw=1')
    raw_body = raw_resp.json()
    assert raw_body.get('status') == 'success'
    assert isinstance(raw_body.get('data'), dict)
    assert 'results' in raw_body['data']
