import json
import pytest
from django.test import RequestFactory, override_settings
from apps.transactions.models import SalesOrder, SalesOrderLine
from apps.transactions.serializers.sales_order_serializers import SalesOrderLineSerializer
from apps.core.views.get_view import WcapiGetView


@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.smoke
@pytest.mark.django_db
def test_sales_order_line_serializer_parent_id_create():
    so = SalesOrder.objects.create()
    ser = SalesOrderLineSerializer(data={"parent_id": so.id})
    assert ser.is_valid(), ser.errors
    obj = ser.save()
    assert isinstance(obj, SalesOrderLine)
    assert getattr(obj, 'parent_id') == so.id


@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.smoke
@pytest.mark.django_db
@override_settings(WCAPI_OPEN_READ=True)
def test_wcapi_get_sales_order_line_has_parent_id():
    so = SalesOrder.objects.create()
    line = SalesOrderLine.objects.create(parent=so)

    rf = RequestFactory()
    req = rf.get("/wcapi/get/", {"model_name": "sales_order_line", "id": line.id})
    response = WcapiGetView.as_view()(req)
    response.render()  # type: ignore[attr-defined]

    assert response.status_code == 200
    body = response.content.decode("utf-8")
    data = json.loads(body)
    rec = data.get("data", {}).get("record", {}) if isinstance(data, dict) else {}
    assert "parent_id" in json.dumps(rec), f"record missing parent_id: {rec}"
    assert "\"parent\":" not in json.dumps(rec), f"record leaked parent key: {rec}"
