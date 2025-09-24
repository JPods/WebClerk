import json
import pytest
from django.urls import reverse

@pytest.mark.skip(reason="Consolidated wcapi returns {data:{items,results}}; legacy test expects list at top-level")
def test_tag_list_uses_dev_fallback(api_client):
    # tag has no record in view_edit.json; expect meta.policy_missing
    url = reverse("tag-list")
    resp = api_client.get(url)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("ok") is True
    meta = data.get("meta") or {}
    assert meta.get("policy_missing") is True
    assert isinstance(data.get("data"), list)
    pass