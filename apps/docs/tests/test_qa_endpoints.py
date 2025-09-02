import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from apps.docs.models.qa import Qa

pytestmark = pytest.mark.django_db

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def user(api_client):
    User = get_user_model()
    u = User.objects.create_user(email='qatester@example.com', password='pw12345', name_first='QA', name_last='Tester', username='')
    api_client.force_authenticate(user=u)
    return u

def test_qa_list_create_and_pagination(api_client, user):
    list_url = reverse('qa-list')
    # create one
    resp = api_client.post(list_url, {'question': 'What is the launch date?', 'answer': 'Q4', 'status':'open', 'security_level':1}, format='json')
    assert resp.status_code in (200,201)
    # bulk create for pagination
    for i in range(30):
        api_client.post(list_url, {'question': f'Q{i}', 'answer': f'A{i}', 'status':'open'}, format='json')
    page1 = api_client.get(list_url)
    assert page1.status_code == 200
    data = page1.json()['data']
    assert len(data['results']) <= 25
    page2 = api_client.get(list_url + '?page=2')
    assert page2.status_code == 200

def test_qa_search_and_highlight(api_client, user):
    q1 = Qa.objects.create(question='Safety checklist item 1', answer='Ensure architecture review complete', status='published', security_level=1)
    q2 = Qa.objects.create(question='Deployment plan', answer='Architecture diagram finalized', status='draft', security_level=2)
    q3 = Qa.objects.create(question='Misc note', answer='General text', status='published', security_level=1)
    for q in (q1,q2,q3):
        q.rebuild_search_vector()
    search_url = reverse('qa-search')
    resp = api_client.get(search_url, {'q':'architecture', 'status':'published', 'level':1})
    assert resp.status_code == 200
    payload = resp.json()['data']
    assert payload['count'] == 1
    first = payload['results'][0]
    assert '<mark>' in first['highlight_snippet']
    # ordering test
    list_url = reverse('qa-list')
    list_resp = api_client.get(list_url + '?ordering=sequence')
    assert list_resp.status_code == 200
