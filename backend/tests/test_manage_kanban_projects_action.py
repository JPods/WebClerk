import uuid

import pytest
from django.contrib.auth import get_user_model

from apps.transactions.models.project import Project


pytestmark = pytest.mark.django_db


def _create_user(role: str = "staff"):
    User = get_user_model()
    suffix = uuid.uuid4().hex[:8]
    return User.objects.create_user(
        username=f"{role}_kanban_{suffix}",
        email=f"{role}_kanban_{suffix}@example.com",
        password="pw12345",
        name_first=role.capitalize(),
        name_last="Tester",
        role=role,
    )


def test_generate_kanban_projects_snaps_to_wednesday(client):
    user = _create_user("staff")
    client.force_login(user)

    resp = client.post(
        "/wcapi/_manage/",
        data={
            "action": "generate_kanban_projects",
            "params": {
                "count": 3,
                "start_date": "2026-04-06",
            },
        },
        content_type="application/json",
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"

    payload = body["data"]
    assert payload["created"] == 3
    assert payload["requested_start_date"] == "2026-04-06"
    assert payload["start_date"] == "2026-04-08"
    assert payload["interval_days"] == 7

    projects = list(Project.objects.filter(id__in=payload["ids"]).order_by("dt_kanban"))
    assert [project.name for project in projects] == [
        "kanban-2026-04-08",
        "kanban-2026-04-15",
        "kanban-2026-04-22",
    ]
    assert [project.dt_kanban.date().isoformat() for project in projects] == [
        "2026-04-08",
        "2026-04-15",
        "2026-04-22",
    ]