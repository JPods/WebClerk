import pytest
from rest_framework.test import APIClient

@pytest.mark.django_db
def test_model_name_list_and_detail(django_user_model):
    user = django_user_model.objects.create_user(email='t@t.com', password='x', role='ADMIN')
    c = APIClient(); c.force_authenticate(user=user)
    resp = c.get('/wcapi/model_name/list/')
    assert resp.status_code == 200
    names = resp.data['data']['model_names']
    assert 'proposal_line' in names and 'sales_order_line' in names
    # detail
    resp2 = c.get('/wcapi/model_name/detail/?model_name=proposal_line')
    assert resp2.status_code == 200
    payload = resp2.data['data']['model']
    assert payload['model_name'] == 'proposal_line'
    assert 'fields' in payload and isinstance(payload['fields'], dict)

@pytest.mark.django_db
def test_no_table_name_accepted_on_settings(django_user_model):
    user = django_user_model.objects.create_user(email='admin@example.com', password='x', role='ADMIN')
    c = APIClient(); c.force_authenticate(user=user)
    bad = {"purpose":"view_edit","model_name":"sales_order_lines","is_active":True,"data":{"ADMIN":{"view":["id"],"edit":[]}}}
    # Even if plural provided, API normalizes to singular and accepts; ensure singular stored
    resp = c.post('/settings/', bad, format='json')
    assert resp.status_code in (200,201)
    got = resp.data['data']
    assert got.get('model_name') == 'sales_order_line'
