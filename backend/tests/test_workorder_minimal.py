import json
import pytest
from django.test import RequestFactory, override_settings


@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.smoke
@pytest.mark.django_db
def test_workorder_line_serializer_parent_id_create():
    from apps.transactions.models import WorkOrder, WorkOrderLine
    from apps.transactions.serializers.workorder_serializer import WorkOrderLineParentIdSerializer as WorkOrderLineSerializer

    wo = WorkOrder.objects.create()
    ser = WorkOrderLineSerializer(data={"parent_id": wo.id})
    assert ser.is_valid(), ser.errors
    obj = ser.save()
    assert isinstance(obj, WorkOrderLine)
    assert obj.workorder_id == wo.id


@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.smoke
@pytest.mark.django_db
def test_wcapi_get_workorder_line_has_parent_id(django_user_model):
    from apps.transactions.models import WorkOrder, WorkOrderLine
    from apps.core.views.wcapi import WCAPIGetView
    from rest_framework.test import force_authenticate

    wo = WorkOrder.objects.create()
    line = WorkOrderLine.objects.create(workorder=wo)

    user = django_user_model.objects.create_superuser(
        email='wo_test@test.com', password='pass1111', username=''
    )

    rf = RequestFactory()
    req = rf.get("/wcapi/get/", {"model_name": "work_order_line", "id": line.id})
    force_authenticate(req, user=user)
    response = WCAPIGetView.as_view()(req)
    response.render()  # type: ignore[attr-defined]

    assert response.status_code == 200
    body = response.content.decode("utf-8")
    data = json.loads(body)
    rec = data.get("data", {}).get("record", {}) if isinstance(data, dict) else {}
    assert "workorder" in rec, f"record missing workorder FK: {rec}"
