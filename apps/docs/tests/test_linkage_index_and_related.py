import json
import pytest

from apps.docs.models.linkage import Linkage
from apps.docs.models.linkage_index import LinkageIndex
from apps.core.models.action import Action
from apps.docs.models.document import Document


@pytest.mark.django_db
def test_linkage_index_uniqueness_add_link_method():
    a = Linkage.objects.create(purpose='t')
    b = Linkage.objects.create(purpose='t')
    # First add succeeds
    assert a.add_link('orders', 1) is True
    a.save()
    # Second add on different linkage should fail
    with pytest.raises(ValueError):
        b.add_link('orders', 1)


@pytest.mark.skip(reason="Legacy linkage-links endpoint removed; canonical model-key API has no links action yet.")
def test_linkage_index_uniqueness_api_conflict(client, django_user_model):
    # Auth
    user = django_user_model.objects.create_user(email='u@example.com', password='p', name_first='U', name_last='Admin', role='admin')
    client.force_login(user)
    a = Linkage.objects.create(purpose='t')
    b = Linkage.objects.create(purpose='t')
    # First link via API
    url_add = reverse('linkage-links', args=[a.id])
    r1 = client.post(url_add, data={'table': 'orders', 'record_id': 2}, content_type='application/json')
    assert r1.status_code == 200
    # Second link on different linkage -> 409
    url_add_b = reverse('linkage-links', args=[b.id])
    r2 = client.post(url_add_b, data={'table': 'orders', 'record_id': 2}, content_type='application/json')
    assert r2.status_code == 409


@pytest.mark.django_db
def test_related_actions_endpoint_lists_action_for_linkage(client, django_user_model):
    user = django_user_model.objects.create_user(email='u2@example.com', password='p', name_first='U2', name_last='Admin', role='admin')
    client.force_login(user)
    lk = Linkage.objects.create(purpose='test')
    # Index mapping for model=linkage record_id=lk.id
    LinkageIndex.objects.create(linkage=lk, table_name='linkages', record_id=lk.id)
    # Create an action linked via linkage id
    act = Action.objects.create(action='test', status='done', refs={'links': {'linkage': [lk.id]}})

    # Canonical: list actions and filter client-side by refs.links.linkage
    res = client.get('/action/?format=json')
    assert res.status_code == 200
    env = res.json()
    data = env.get('data', env)
    items = data.get('items', [])
    ids = [row.get('id') for row in items
           if lk.id in (row.get('refs') or {}).get('links', {}).get('linkage', [])]
    assert act.id in ids


@pytest.mark.django_db
def test_related_documents_endpoint_lists_documents_for_linkage(client, django_user_model):
    user = django_user_model.objects.create_user(email='u3@example.com', password='p', name_first='U3', name_last='Admin', role='admin')
    client.force_login(user)
    # Create doc and linkage with link
    doc = Document.objects.create(name='Doc A')
    lk = Linkage.objects.create(purpose='test', refs={'links': {'documents': [doc.id]}})
    LinkageIndex.objects.create(linkage=lk, table_name='linkages', record_id=lk.id)

    # Canonical: query documents by id__in using linkage refs
    doc_ids = lk.refs.get('links', {}).get('documents', [])
    payload = {'model': 'document', 'filters': {'id__in': doc_ids}}
    res = client.post('/wcapi/query', data=json.dumps(payload), content_type='application/json')
    assert res.status_code == 200
    env = res.json()
    data = env.get('data', env)
    items = data.get('items', [])
    ids = [row.get('id') for row in items]
    assert doc.id in ids


@pytest.mark.django_db
def test_rebuild_linkage_index_command_creates_rows(django_user_model):
    lk = Linkage.objects.create(purpose='rebuild', refs={'links': {'foo': [123, 456]}})
    # Ensure no rows
    LinkageIndex.objects.all().delete()
    from django.core.management import call_command
    call_command('rebuild_linkage_index', purge=False, batch=100, limit=0)
    rows = list(LinkageIndex.objects.filter(linkage=lk, table_name='foo').order_by('record_id'))
    assert [r.record_id for r in rows] == [123, 456]
