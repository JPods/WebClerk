import json
import pytest
from django.test import RequestFactory, override_settings
from apps.transactions.models import Invoice, InvoiceLine
from apps.transactions.serializers.invoice_serializers import InvoiceLineSerializer
from apps.core.views.get_view import WcapiGetView


@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.smoke
@pytest.mark.django_db
def test_invoice_line_serializer_parent_id_create():
    inv = Invoice.objects.create()
    ser = InvoiceLineSerializer(data={"parent_id": inv.id})
    assert ser.is_valid(), ser.errors
    obj = ser.save()
    assert isinstance(obj, InvoiceLine)
    # Access runtime attribute parent_id (provided by Django FK); mypy may not know it.
    assert getattr(obj, 'parent_id') == inv.id


@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.smoke
@pytest.mark.django_db
@override_settings(WCAPI_OPEN_READ=True)
def test_wcapi_get_invoice_line_has_parent_id():
    inv = Invoice.objects.create()
    line = InvoiceLine.objects.create(parent=inv)

    rf = RequestFactory()
    req = rf.get("/wcapi/get/", {"model_name": "invoice_line", "id": line.id})
    # No auth due to WCAPI_OPEN_READ=True
    response = WcapiGetView.as_view()(req)
    # Render for content access
    response.render()  # type: ignore[attr-defined]

    assert response.status_code == 200
    body = response.content.decode("utf-8")
    data = json.loads(body)
    rec = data.get("data", {}).get("record", {}) if isinstance(data, dict) else {}
    # Ensure parent_id present and parent absent
    assert "parent_id" in json.dumps(rec), f"record missing parent_id: {rec}"
    assert "\"parent\":" not in json.dumps(rec), f"record leaked parent key: {rec}"
