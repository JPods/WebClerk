import json
import pytest
from tests.utils import assert_envelope


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
    body = resp.json()
    assert_envelope(body, expect_status='fail')
    assert 'Missing model_name' in body['message']  #chaned from t_n


@pytest.mark.django_db
def test_wcapi_unknown_table_post(client, user1):
    client.force_login(user1)
    resp = client.post('/wcapi/query/', data=json.dumps({'model_name': 'nope'}), content_type='application/json')  #chaned from t_n
    assert resp.status_code == 400
    body = resp.json()
    assert_envelope(body, expect_status='fail')
    assert body['message'] == 'Unknown model'  #chaned from t_n


@pytest.mark.django_db
def test_wcapi_invalid_json_post(client, user1):
    client.force_login(user1)
    resp = client.post('/wcapi/query/', data='{"bad"', content_type='application/json')
    assert resp.status_code == 400
    body = resp.json()
    assert_envelope(body, expect_status='fail')
    assert 'Invalid JSON' in body['message']


@pytest.mark.django_db
def test_save_missing_table(client, user2):
    client.force_login(user2)
    resp = client.post('/wcapi/save/', data=json.dumps({'name_first': 'A'}), content_type='application/json')
    assert resp.status_code == 400
    body = resp.json()
    assert_envelope(body, expect_status='fail')
    assert 'Missing required field' in body['message']


@pytest.mark.django_db
def test_save_unknown_table(client, user2):
    client.force_login(user2)
    resp = client.post('/wcapi/save/', data=json.dumps({'model_name': 'nope'}), content_type='application/json')  #chaned from t_n
    assert resp.status_code == 400
    body = resp.json()
    assert_envelope(body, expect_status='fail')
    assert 'Unknown model' in body['message']  #chaned from t_n


@pytest.mark.django_db
def test_save_invalid_json(client, user2):
    client.force_login(user2)
    resp = client.post('/wcapi/save/', data='{"oops"', content_type='application/json')
    assert resp.status_code == 400
    body = resp.json()
    assert_envelope(body, expect_status='fail')
    assert 'Invalid JSON' in body['message']
