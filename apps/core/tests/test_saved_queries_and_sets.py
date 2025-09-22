import pytest
from django.urls import reverse
from django.contrib.auth.models import User
from apps.core.models import Setting

@pytest.mark.django_db
def test_create_saved_query_person_scope(client):
    u = User.objects.create_user(username="alice", password="x")
    client.force_login(u)
    url = f"/wcapi/contact/_query/save"
    payload = {
        "name": "My Contacts",
        "dsl": {"where": [{"field": "company", "op": "icontains", "value": "Acme"}]},
        "scope": {"type": "person", "value": str(u.id)},
        "labels": ["fav"],
        "comment": "test",
    }
    resp = client.post(url, data=payload, content_type="application/json")
    assert resp.status_code == 200
    data = resp.json()
    row = Setting.objects.get(pk=data["id"])
    assert row.purpose == "saved_query"
    assert row.model_name == "contact"
    assert (row.data or {}).get("owner_id") == u.id

@pytest.mark.django_db
def test_saved_set_add_remove(client):
    u = User.objects.create_user(username="bob", password="x")
    client.force_login(u)
    # create set
    url = f"/wcapi/contact/_sets"
    resp = client.post(url, data={"name": "S1", "ids": [1,2,3], "scope": {"type": "person", "value": str(u.id)}}, content_type="application/json")
    assert resp.status_code == 200
    s = resp.json()["id"]
    # remove
    url_item = f"/wcapi/contact/_sets/{s}"
    resp = client.patch(url_item, data={"op": "remove", "ids": [2]}, content_type="application/json")
    assert resp.status_code == 200
    row = Setting.objects.get(pk=s)
    assert sorted((row.data or {}).get("ids")) == [1,3]