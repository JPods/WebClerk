import json
import pytest
from django.test import RequestFactory, override_settings


@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.smoke
@pytest.mark.django_db
def test_order_line_serializer_parent_id_create():
    from apps.transactions.models import Order, OrderLine
    from apps.transactions.serializers.order_serializers import OrderLineSerializer

    so = Order.objects.create()
    ser = OrderLineSerializer(data={"parent_id": so.id})
    assert ser.is_valid(), ser.errors
    obj = ser.save()
    assert isinstance(obj, OrderLine)
    assert obj.order_id == so.id


@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.smoke
@pytest.mark.django_db
def test_wcapi_get_order_line_has_parent_id(django_user_model):
    from apps.transactions.models import Order, OrderLine
    from apps.core.views.wcapi import WCAPIGetView
    from rest_framework.test import force_authenticate

    so = Order.objects.create()
    line = OrderLine.objects.create(order=so)

    user = django_user_model.objects.create_superuser(
        email='ord_test@test.com', password='pass1111', username=''
    )

    rf = RequestFactory()
    req = rf.get("/wcapi/get/", {"model_name": "order_line", "id": line.id})
    force_authenticate(req, user=user)
    response = WCAPIGetView.as_view()(req)
    response.render()  # type: ignore[attr-defined]

    assert response.status_code == 200
    body = response.content.decode("utf-8")
    data = json.loads(body)
    rec = data.get("data", {}).get("record", {}) if isinstance(data, dict) else {}
    assert "order" in rec, f"record missing order FK: {rec}"
