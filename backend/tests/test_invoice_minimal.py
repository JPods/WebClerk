import json
import pytest
from django.test import RequestFactory, override_settings


@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.smoke
@pytest.mark.django_db
def test_invoice_line_serializer_parent_id_create():
    from apps.transactions.models import Invoice, InvoiceLine
    from apps.transactions.serializers.invoice_serializers import InvoiceLineSerializer

    inv = Invoice.objects.create()
    ser = InvoiceLineSerializer(data={"parent_id": inv.id})
    assert ser.is_valid(), ser.errors
    obj = ser.save()
    assert isinstance(obj, InvoiceLine)
    # Access runtime attribute parent_id (provided by Django FK); mypy may not know it.
    assert obj.invoice_id == inv.id


@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.smoke
@pytest.mark.django_db
def test_wcapi_get_invoice_line_has_parent_id(django_user_model):
    from apps.transactions.models import Invoice, InvoiceLine
    from apps.core.views.wcapi import WCAPIGetView
    from rest_framework.test import force_authenticate

    inv = Invoice.objects.create()
    line = InvoiceLine.objects.create(invoice=inv)

    user = django_user_model.objects.create_superuser(
        email='inv_test@test.com', password='pass1111', username=''
    )

    rf = RequestFactory()
    req = rf.get("/wcapi/get/", {"model_name": "invoice_line", "id": line.id})
    force_authenticate(req, user=user)
    response = WCAPIGetView.as_view()(req)
    # Render for content access
    response.render()  # type: ignore[attr-defined]

    assert response.status_code == 200
    body = response.content.decode("utf-8")
    data = json.loads(body)
    rec = data.get("data", {}).get("record", {}) if isinstance(data, dict) else {}
    # Ensure invoice_id present in the serialized record
    assert "invoice" in rec, f"record missing invoice FK: {rec}"
