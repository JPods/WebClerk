import pytest
from rest_framework.test import APIClient
from apps.transactions.models import Proposal, ProposalLine
from apps.core.models.setting import Setting


def _auth_client(user):
    from rest_framework_simplejwt.tokens import RefreshToken
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {RefreshToken.for_user(user).access_token}')
    return client

@pytest.mark.django_db
def test_field_auth_matrix_endpoint(django_user_model):
    Setting.objects.create(purpose='wc:view_edit', model_target='proposal_line', is_active=True,
                           data={"USER": {"view": ["id", "status"], "edit": ["status"]}})
    user = django_user_model.objects.create_user(email='user1@example.com', password='pass12345', role='USER')
    client = _auth_client(user)
    resp = client.get('/tx/auth/fields/?model=proposal-line')  # type: ignore
    assert resp.status_code == 200  # type: ignore[attr-defined]
    assert resp.data['data']['rules']['view'] == ['id', 'status']  # type: ignore[attr-defined]
    assert resp.data['data']['rules']['edit'] == ['status']  # type: ignore[attr-defined]

@pytest.mark.django_db
def test_serializer_field_filtering(django_user_model):
    Setting.objects.create(purpose='wc:view_edit', model_target='proposal_line', is_active=True,
                           data={"USER": {"view": ["id", "status"], "edit": ["status"]}})
    user = django_user_model.objects.create_user(email='user2@example.com', password='pass12345', role='USER')
    parent = Proposal.objects.create()
    ProposalLine.objects.create(parent=parent, parent_ref_id=parent.pk, status='OPEN')
    client = _auth_client(user)
    resp = client.get(f'/tx/proposal-lines/?parent_ref_id={parent.pk}')  # type: ignore
    assert resp.status_code == 200  # type: ignore[attr-defined]
    data = resp.data['data']  # type: ignore[attr-defined]
    item = data['results'][0]
    assert 'status' in item and 'probability' not in item

@pytest.mark.django_db
def test_disallowed_edit(django_user_model):
    Setting.objects.create(purpose='wc:view_edit', model_target='proposal_line', is_active=True,
                           data={"USER": {"view": ["id", "status"], "edit": []}})
    user = django_user_model.objects.create_user(email='user3@example.com', password='pass12345', role='USER')
    parent = Proposal.objects.create()
    line = ProposalLine.objects.create(parent=parent, parent_ref_id=parent.pk, status='OPEN')
    client = _auth_client(user)
    resp = client.patch(f'/tx/proposal-lines/{line.pk}/', {'status': 'CLOSED'}, format='json')  # type: ignore
    assert resp.status_code in (400, 403)  # type: ignore[attr-defined]

@pytest.mark.django_db
def test_view_edit_cache_invalidation(django_user_model):
    setting = Setting.objects.create(purpose='wc:view_edit', model_target='proposal_line', is_active=True,
                                     data={"USER": {"view": ["id"], "edit": []}})
    user = django_user_model.objects.create_user(email='cachetest@example.com', password='pass12345', role='USER')
    parent = Proposal.objects.create()
    ProposalLine.objects.create(parent=parent, parent_ref_id=parent.pk, status='OPEN')
    client = _auth_client(user)
    resp1 = client.get(f'/tx/proposal-lines/?parent_ref_id={parent.pk}')  # type: ignore
    assert resp1.status_code == 200  # type: ignore[attr-defined]
    data1 = resp1.data['data']  # type: ignore[attr-defined]
    item1 = data1['results'][0]
    assert 'status' not in item1
    # Modify setting to include status
    setting.data['USER']['view'].append('status')  # type: ignore[index]
    setting.save()
    resp2 = client.get(f'/tx/proposal-lines/?parent_ref_id={parent.pk}')  # type: ignore
    assert resp2.status_code == 200  # type: ignore[attr-defined]
    data2 = resp2.data['data']  # type: ignore[attr-defined]
    item2 = data2['results'][0]
    assert 'status' in item2

@pytest.mark.django_db
def test_setting_invalid_model_target_rejected(django_user_model):
    user = django_user_model.objects.create_user(email='invalidtbl@example.com', password='pass12345', role='ADMIN')
    client = _auth_client(user)
    payload = {"purpose": "view_edit", "model_target": "not_a_model", "is_active": True, "data": {"ADMIN": {"view": ["id"], "edit": []}}}
    resp = client.post('/settings/', payload, format='json')  # type: ignore
    # Expect 400 with specific error
    assert resp.status_code == 400  # type: ignore[attr-defined]
    assert 'model_target' in (resp.data.get('error', {}).get('details', {}) if hasattr(resp, 'data') else {})  # type: ignore[attr-defined]
