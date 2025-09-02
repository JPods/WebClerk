import pytest
from django.urls import reverse
from rest_framework import status

pytestmark = pytest.mark.django_db


def test_not_found_enveloped(client):
    r = client.get('/this/path/does/not/exist/')
    assert r.status_code == 404
    body = r.json()
    assert body.get('status') == 'fail'
    assert body.get('error', {}).get('code') == 'not_found'


def test_validation_error_enveloped(client, django_user_model):
    # Force auth for an endpoint expecting payload to produce validation error
    user = django_user_model.objects.create_user(email='vtest@example.com', password='pw', name_first='V', name_last='Test')
    client.force_login(user)
    # Use domain create without required field 'path' to trigger validation error
    create_url = reverse('communications:domain-list')
    r = client.post(create_url, {'type': 'website'})
    assert r.status_code in (400, 403)  # if permission denies, still enveloped
    body = r.json()
    assert 'status' in body and body['status'] in ('fail','error')  # 4xx -> fail
    assert 'error' in body and 'code' in body['error']
    # Accept either forbidden or validation_error
    assert body['error']['code'] in {'validation_error', 'forbidden'}
