import json
import pytest
from tests.utils import assert_envelope, wcapi_save


@pytest.fixture
def user1(django_user_model):
    return django_user_model.objects.create_user(email='u1@example.com', password='pw', name_first='U', name_last='One')


@pytest.fixture
def user2(django_user_model):
    return django_user_model.objects.create_user(email='u2@example.com', password='pw', name_first='U', name_last='Two')


@pytest.mark.django_db
def test_wcapi_unknown_table_get(client, user1):
    """GET /wcapi/<model>/ for a model that does not exist is refused."""
    client.force_login(user1)
    resp = client.get('/wcapi/nope/')
    assert resp.status_code == 400
    body = resp.json()
    assert_envelope(body, expect_status='fail')
    assert 'nope' in body['message'].lower()


@pytest.mark.django_db
def test_the_old_get_route_is_gone(client, user1):
    """GET /wcapi/get/ was the verb in the path; REST reads are GET /wcapi/<model>/."""
    client.force_login(user1)
    resp = client.get('/wcapi/get/', {'model_name': 'contact'})
    assert resp.status_code in (400, 404)


@pytest.mark.django_db
def test_save_unknown_table(client, user2):
    client.force_login(user2)
    resp = wcapi_save(client, data=json.dumps({'model_name': 'nope'}), content_type='application/json')
    assert resp.status_code == 400
    body = resp.json()
    assert_envelope(body, expect_status='fail')
    assert 'Unknown model' in body['message']


@pytest.mark.django_db
def test_save_invalid_json(client, user2):
    client.force_login(user2)
    resp = client.post('/wcapi/contact/', data='{"oops"', content_type='application/json')
    assert resp.status_code == 400
    body = resp.json()
    assert_envelope(body, expect_status='fail')
    assert 'JSON parse error' in body['message']


@pytest.mark.django_db
def test_an_update_needs_the_record_in_the_path(client, user2):
    client.force_login(user2)
    resp = client.put('/wcapi/contact/', data=json.dumps({'name_first': 'A'}), content_type='application/json')
    assert resp.status_code == 405
    assert resp.json()['error']['code'] == 'method_not_allowed'


@pytest.mark.django_db
def test_an_id_in_a_create_body_is_refused(client, user2):
    client.force_login(user2)
    resp = client.post('/wcapi/contact/', data=json.dumps({'id': 5}), content_type='application/json')
    assert resp.status_code == 400
    assert resp.json()['error']['code'] == 'id_in_body'
