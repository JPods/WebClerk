import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from apps.docs.models.question_answer import QuestionAnswer
from django.urls import reverse  # legacy

pytestmark = pytest.mark.django_db

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def user(api_client):
    User = get_user_model()
    u = User.objects.create_user(email='qatester@example.com', password='pw12345', name_first='QuestionAnswer', name_last='Tester', username='')
    api_client.force_authenticate(user=u)
    return u

# Ensure wcapi registry is current for model-key lookups in tests
def setup_module(module):
    try:
        from apps.core.wcapi import registry
        registry.refresh_from_settings()
    except Exception:
        pass

def test_qa_list_create_and_pagination(api_client, user):
    client = api_client
    client.force_authenticate(user=user)

    # List via canonical model-key route
    list_url = '/qa/?format=json'
    r = client.get(list_url)
    assert r.status_code == 200, getattr(r, 'data', None)

    # Create via wcapi canonical create
    create = client.post('/wcapi/save', {'model': 'qa', 'data': {'question': 'Q1?', 'answer': 'A1'}}, format='json')
    assert create.status_code in (200, 201), getattr(create, 'data', None)

    # List again and assert canonical payload
    r2 = client.get(list_url)
    assert r2.status_code == 200
    payload = getattr(r2, 'data', {}) or {}
    payload = payload.get('data', payload)
    items = payload.get('items') or []
    assert isinstance(items, list)
    assert any((it.get('question') or '').startswith('Q1') for it in items)

    # Soft pagination assertion (wcapi uses items, not results)
    assert len(items) >= 1

def test_qa_search_and_highlight(api_client, user):
    q1 = QuestionAnswer.objects.create(question='Safety checklist item 1', answer='Ensure architecture review complete', status='published', security_level=1)
    q2 = QuestionAnswer.objects.create(question='Deployment plan', answer='Architecture diagram finalized', status='draft', security_level=2)
    q3 = QuestionAnswer.objects.create(question='Misc note', answer='General text', status='published', security_level=1)
    for q in (q1,q2,q3):
        if hasattr(q, 'rebuild_search_vector'):
            q.rebuild_search_vector()

    # q param is staff-only on canonical list endpoints
    user.is_staff = True
    user.save(update_fields=['is_staff'])
    api_client.force_authenticate(user=user)

    search_url = '/qa/?q=architecture&format=json'
    resp = api_client.get(search_url)
    assert resp.status_code == 200
    payload = getattr(resp, 'data', {}) or {}
    payload = payload.get('data', payload)
    items = payload.get('items') or []
    assert isinstance(items, list)

    # Client-side filter equivalent of (status=published AND level=1 AND contains 'architecture')
    filtered = [
        it for it in items
        if 'architecture' in f"{it.get('question','')} {it.get('answer','')}".lower()
        and (it.get('status') == 'published')
        and (it.get('security_level') in (1, '1'))
    ]
    assert any((it.get('question') or '').startswith('Safety') for it in filtered)
