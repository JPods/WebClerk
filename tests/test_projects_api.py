import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from typing import cast
from apps.transactions.models.projects import Project

@pytest.mark.django_db
def test_project_create_and_list(admin_user):
    client = APIClient()
    client.force_authenticate(user=admin_user)
    resp = client.post(reverse('project-list'), {
        'situation': 'Inventory accuracy falling',
        'objective': {'summary': 'Improve inventory accuracy', 'success': {'definition': '>=98%', 'metrics': []}},
        'priority': 2,
        'status': 'active',
        'attention': 'high',
        'intent': 'Stabilize DC operations',
        'category': 'ops'
    }, format='json')
    assert resp.status_code == 201, getattr(resp, 'data', None)  # type: ignore[attr-defined]
    pid = resp.data['data']['id']  # type: ignore[attr-defined]

    # list + pagination basics
    list_resp = client.get(reverse('project-list'))
    assert list_resp.status_code == 200  # type: ignore[attr-defined]
    assert any(p['id'] == pid for p in list_resp.data['data']['results'])  # type: ignore[attr-defined]

@pytest.mark.django_db
def test_project_validation_priority(admin_user):
    client = APIClient()
    client.force_authenticate(user=admin_user)
    bad = client.post(reverse('project-list'), {'priority': 99}, format='json')
    assert bad.status_code == 400  # type: ignore[attr-defined]
    # Validation errors now under error.details
    assert 'priority' in (bad.data.get('error', {}).get('details') or {})  # type: ignore[attr-defined]

@pytest.mark.django_db
def test_project_task_burndown_derivation(admin_user):
    client = APIClient()
    client.force_authenticate(user=admin_user)
    resp = client.post(reverse('project-list'), {
        'tasks': {'items': [
            {'id':1,'title':'A','done':True},
            {'id':2,'title':'B','done':False},
            {'id':3,'title':'C','done':False}
        ]}
    }, format='json')
    assert resp.status_code == 201, getattr(resp, 'data', None)  # type: ignore[attr-defined]
    proj = Project.objects.get(id=resp.data['data']['id'])  # type: ignore[attr-defined]
    # 1 of 3 done => ~33 => stored burndown rounded int
    assert 30 <= proj.burndown <= 35
