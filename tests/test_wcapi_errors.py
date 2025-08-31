import json
import pytest


@pytest.fixture
def user1(django_user_model):
    return django_user_model.objects.create_user(email='u1@example.com', password='pw', name_first='U', name_last='One')


@pytest.fixture
def user2(django_user_model):
    return django_user_model.objects.create_user(email='u2@example.com', password='pw', name_first='U', name_last='Two')


@pytest.mark.django_db
def test_wcapi_missing_table_name_get(client, user1):
    client.force_login(user1)
    resp = client.get('/wcapi/query/')
    assert resp.status_code == 400
    data = resp.json()
    assert data['status'] == 'error'
    assert 'Missing table_name' in data['message']


@pytest.mark.django_db
def test_wcapi_unknown_table_post(client, user1):
    client.force_login(user1)
    resp = client.post('/wcapi/query/', data=json.dumps({'table_name': 'nope'}), content_type='application/json')
    assert resp.status_code == 400
    data = resp.json()
    assert data['status'] == 'error'
    assert data['message'] == 'Unknown table'


@pytest.mark.django_db
def test_wcapi_invalid_json_post(client, user1):
    client.force_login(user1)
    resp = client.post('/wcapi/query/', data='{"bad"', content_type='application/json')
    assert resp.status_code == 400
    data = resp.json()
    assert data['status'] == 'error'
    assert 'Invalid JSON' in data['message']


@pytest.mark.django_db
def test_save_missing_table(client, user2):
    client.force_login(user2)
    resp = client.post('/wcapi/save/', data=json.dumps({'name_first': 'A'}), content_type='application/json')
    assert resp.status_code == 400
    data = resp.json()
    assert data['status'] == 'error'
    assert 'Missing required field' in data['message']


@pytest.mark.django_db
def test_save_unknown_table(client, user2):
    client.force_login(user2)
    resp = client.post('/wcapi/save/', data=json.dumps({'table_name': 'nope'}), content_type='application/json')
    assert resp.status_code == 400
    data = resp.json()
    assert data['status'] == 'error'
    assert 'Unknown table' in data['message']


@pytest.mark.django_db
def test_save_invalid_json(client, user2):
    client.force_login(user2)
    resp = client.post('/wcapi/save/', data='{"oops"', content_type='application/json')
    assert resp.status_code == 400
    data = resp.json()
    assert data['status'] == 'error'
    assert 'Invalid JSON' in data['message']
