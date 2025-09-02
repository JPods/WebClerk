import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from apps.docs.models.tag import Tag

pytestmark = pytest.mark.django_db

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def user(api_client):
    User = get_user_model()
    u = User.objects.create_user(email='tagtester@example.com', password='pw12345', name_first='Tag', name_last='Tester', username='')
    api_client.force_authenticate(user=u)
    return u

def test_tag_list_create_and_pagination(api_client, user):
    list_url = reverse('tag-list')
    r = api_client.post(list_url, {'name':'T1','purpose':'track','status':'active','table_name':'shipments','record_id':1}, format='json')
    assert r.status_code in (200,201)
    for i in range(30):
        api_client.post(list_url, {'name':f'T{i}','purpose':'batch','table_name':'equip','record_id':i}, format='json')
    page1 = api_client.get(list_url)
    assert page1.status_code == 200
    data = page1.json()['data']
    assert len(data['results']) <= 25
    page2 = api_client.get(list_url + '?page=2')
    assert page2.status_code == 200


def test_tag_hierarchy_and_filters(api_client, user):
    parent = Tag.objects.create(name='Pallet A', purpose='logistics', status='active')
    child1 = Tag.objects.create(name='Box 1', purpose='logistics', status='active')
    child2 = Tag.objects.create(name='Box 2', purpose='logistics', status='inactive')
    list_url = reverse('tag-list')
    # filter by purpose
    resp = api_client.get(list_url + '?purpose=logistics')
    assert resp.status_code == 200
    # hierarchy ops
    hier_url = reverse('tag-hierarchy', args=[parent.id])
    add1 = api_client.post(hier_url, {'child_id': child1.id}, format='json')
    assert add1.status_code == 200
    add2 = api_client.post(hier_url, {'child_id': child2.id}, format='json')
    assert add2.status_code == 200
    # remove one
    rem = api_client.delete(hier_url, {'child_id': child1.id}, format='json')
    assert rem.status_code == 200
    # set parent on child2
    set_parent = api_client.patch(reverse('tag-hierarchy', args=[child2.id]), {'parent_id': parent.id}, format='json')
    assert set_parent.status_code == 200
    # retrieve increments access
    detail = api_client.get(reverse('tag-detail', args=[parent.id]))
    assert detail.status_code == 200


def test_tag_search_and_bulk_hierarchy(api_client, user):
    # create tags
    t_parent = Tag.objects.create(name='Pallet Loader', purpose='logistics ops', status='active')
    t_child_a = Tag.objects.create(name='Pallet Location A', purpose='logistics', status='active')
    t_child_b = Tag.objects.create(name='Pallet Location B', purpose='logistics', status='active')
    t_inactive = Tag.objects.create(name='Pallet Old', purpose='logistics', status='inactive', is_active=False)

    # search multi-term prefix (should match parent and children but exclude inactive)
    search_url = reverse('tag-search') + '?q=Pallet Lo'
    resp = api_client.get(search_url)
    assert resp.status_code == 200
    data = resp.json()['data']
    names = {r['name'] for r in data['results']}
    assert 'Pallet Loader' in names
    assert 'Pallet Location A' in names
    assert 'Pallet Location B' in names
    assert 'Pallet Old' not in names  # inactive excluded

    # bulk add children
    hier_url = reverse('tag-hierarchy', args=[t_parent.id])
    add_bulk = api_client.post(hier_url, {'child_ids': [t_child_a.id, t_child_b.id]}, format='json')
    assert add_bulk.status_code == 200
    children_after_add = set(add_bulk.json()['data'].get('children', []))
    assert t_child_a.id in children_after_add and t_child_b.id in children_after_add

    # bulk remove children
    rem_bulk = api_client.delete(hier_url, {'child_ids': [t_child_a.id, t_child_b.id]}, format='json')
    assert rem_bulk.status_code == 200
    children_after_remove = set(rem_bulk.json()['data'].get('children', []))
    assert t_child_a.id not in children_after_remove and t_child_b.id not in children_after_remove

    # confirm include_inactive brings back the inactive one in list
    list_with_inactive = api_client.get(reverse('tag-list') + '?include_inactive=1')
    assert list_with_inactive.status_code == 200
    list_data = list_with_inactive.json()['data']
    result_list = list_data['results']
    assert any(r['name'] == 'Pallet Old' for r in result_list)
