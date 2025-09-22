import pytest
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from apps.core.models import Setting
from typing import List, cast

def _make_user(username="alice", email="alice@example.com", password="x"):
    UserModel = get_user_model()
    field_names = {f.name for f in UserModel._meta.get_fields()}
    kwargs = {"password": password}
    if "email" in field_names:
        kwargs["email"] = email
    if "username" in field_names:
        kwargs["username"] = username
    return UserModel.objects.create_user(**kwargs)

@pytest.mark.django_db
def test_create_saved_query_person_scope(client):
    u = _make_user()
    client.force_login(u)
    url = f"/wcapi/contact/_query/save"
    payload = {
        "name": "My Contacts",
        "dsl": {"where": [{"field": "company", "op": "icontains", "value": "Acme"}]},
        "scope": {"type": "person", "value": str(u.pk)},
        "labels": ["fav"],
        "comment": "test",
    }
    resp = client.post(url, data=payload, content_type="application/json")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("ok") is True
    assert data.get("id")

@pytest.mark.django_db
def test_saved_set_add_remove(client):
    u = User.objects.create_user(username="bob", password="x")
    client.force_login(u)
    # create set
    url = f"/wcapi/contact/_sets"
    resp = client.post(url, data={"name": "S1", "ids": [1,2,3], "scope": {"type": "person", "value": str(u.pk)}}, content_type="application/json")
    assert resp.status_code == 200
    s = resp.json()["id"]
    # remove
    url_item = f"/wcapi/contact/_sets/{s}"
    resp = client.patch(url_item, data={"op": "remove", "ids": [2]}, content_type="application/json")
    row = Setting.objects.get(pk=s)
    ids = cast(List[int], ((row.data or {}).get("ids") or []))
    assert sorted(ids) == [1,3]
    assert sorted(cast(List[int], (row.data or {}).get("ids") or [])) == [1,3]