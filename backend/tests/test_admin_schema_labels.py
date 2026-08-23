from django.contrib import admin
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

from apps.transactions.admin import InvoiceAdmin
from apps.transactions.models import Invoice


def test_schema_labels_mixin_rewrites_plain_field_list_headers():
    request = RequestFactory().get("/admin/")
    model_admin = InvoiceAdmin(Invoice, admin.site)

    list_display = model_admin.get_list_display(request)

    assert callable(list_display[0])
    assert getattr(list_display[0], "short_description", None) == "id"


def test_schema_labels_mixin_keeps_explicit_admin_methods():
    request = RequestFactory().get("/admin/")
    model_admin = InvoiceAdmin(Invoice, admin.site)

    list_display = model_admin.get_list_display(request)

    assert "totals_total" in list_display


def test_schema_labels_mixin_sets_form_labels_to_field_names():
    request = RequestFactory().get("/admin/")
    request.user = AnonymousUser()
    model_admin = InvoiceAdmin(Invoice, admin.site)

    form_class = model_admin.get_form(request)

    assert form_class.base_fields["status"].label == "status"
