from django.contrib import admin, messages
from django.db import models as dj_models
from django.utils.html import format_html
from datetime import datetime
from common.admin_schema_labels import SchemaLabelsAdminMixin
from common.admin_mixins import ScalarFirstFieldsetMixin
from .models import (
    Invoice, InvoiceLine,
    WorkOrderLine, Order, OrderLine, Purchase, PurchaseLine,
    Proposal, ProposalLine, Requisition, RequisitionLine, WorkOrder,
    Project, Payment, PaymentMethod, PaymentTerm,
)
from .models.receipt import Receipt
from .models.payment_application import PaymentApplication


class TransactionTotalsDisplayMixin:
    """Display computed totals from JSON totals field and format dt_created as date."""

    def _get_totals(self, obj):
        """Get totals as dict, handling string JSON or dict."""
        import json
        totals = getattr(obj, 'totals', None)
        if totals is None:
            return {}
        if isinstance(totals, str):
            try:
                return json.loads(totals)
            except (json.JSONDecodeError, TypeError):
                return {}
        return totals if isinstance(totals, dict) else {}

    @admin.display(description=".total")
    def totals_total(self, obj):
        totals = self._get_totals(obj)
        val = totals.get('total')
        return f"{val:,.2f}" if val is not None else "0.00"

    @admin.display(description=".cost")
    def totals_cost(self, obj):
        totals = self._get_totals(obj)
        val = totals.get('cost')
        return f"{val:,.2f}" if val is not None else "0.00"

    @admin.display(description=".margin_pc")
    def totals_margin_pc(self, obj):
        totals = self._get_totals(obj)
        val = totals.get('margin_pc')
        return f"{val:.1f}%" if val is not None else "-"

    @admin.display(description=".balance")
    def totals_balance(self, obj):
        totals = self._get_totals(obj)
        val = totals.get('balance')
        return f"{val:,.2f}" if val is not None else "0.00"

    @admin.display(description="dt_created")
    def date_created(self, obj):
        dt = getattr(obj, 'dt_created', None)
        if dt is None:
            return "-"
        # dt_created is milliseconds since epoch
        if isinstance(dt, (int, float)):
            return datetime.fromtimestamp(dt / 1000).strftime("%Y-%m-%d")
        return str(dt)[:10] if dt else "-"


class LineDisplayMixin:
    """Display computed fields from JSON item and quantity fields for line models."""

    def _get_json_field(self, obj, field_name):
        """Get JSON field as dict, handling string JSON or dict."""
        import json
        val = getattr(obj, field_name, None)
        if val is None:
            return {}
        if isinstance(val, str):
            try:
                return json.loads(val)
            except (json.JSONDecodeError, TypeError):
                return {}
        return val if isinstance(val, dict) else {}

    @admin.display(description=".staged")
    def qty_staged(self, obj):
        quantity = self._get_json_field(obj, 'quantity')
        val = quantity.get('staged') or quantity.get('active')
        return val if val is not None else "-"

    @admin.display(description=".ida_item")
    def item_ida_item(self, obj):
        item = self._get_json_field(obj, 'item')
        return item.get('ida_item') or "-"

    @admin.display(description=".description")
    def item_description(self, obj):
        item = self._get_json_field(obj, 'item')
        desc = item.get('description') or ""
        return desc[:50] + "..." if len(desc) > 50 else desc or "-"


class JSONBFieldsetMixin:
    """Group JSON-heavy fields at the end of the admin form."""

    readonly_auto_fields: tuple[str, ...] = ("id", "uuid", "dt_created", "dt_modified", "version")
    details_fieldset_title = "Record Details"
    jsonb_fieldset_title = "JSONB Payloads"

    def get_readonly_fields(self, request, obj=None):  # type: ignore[override]
        readonly = list(super().get_readonly_fields(request, obj))
        for field_name in self.readonly_auto_fields:
            if hasattr(self.model, field_name) and field_name not in readonly:
                readonly.append(field_name)
        return tuple(readonly)

    def _jsonb_field_names(self) -> tuple[str, ...]:
        names: list[str] = []
        for field in self.model._meta.get_fields():
            if getattr(field, "auto_created", False):
                continue
            if isinstance(field, dj_models.JSONField):
                names.append(field.name)
        return tuple(sorted(dict.fromkeys(names)))

    def _non_jsonb_field_names(self) -> tuple[str, ...]:
        json_fields = set(self._jsonb_field_names())
        names: list[str] = []
        for field in self.model._meta.fields:
            if field.name in json_fields:
                continue
            names.append(field.name)
        return tuple(names)

    def get_fieldsets(self, request, obj=None):  # type: ignore[override]
        detail_fields = self._non_jsonb_field_names()
        json_fields = self._jsonb_field_names()
        fieldsets: list[tuple[str, dict]] = []
        if detail_fields:
            fieldsets.append((self.details_fieldset_title, {"fields": detail_fields}))
        if json_fields:
            fieldsets.append((self.jsonb_fieldset_title, {"fields": json_fields}))
        if fieldsets:
            return tuple(fieldsets)
        return super().get_fieldsets(request, obj)


##


##


##

@admin.register(Invoice)
class InvoiceAdmin(SchemaLabelsAdminMixin, TransactionTotalsDisplayMixin, JSONBFieldsetMixin, admin.ModelAdmin):
    # Scalar fields: address_full, attention, balance, conditions_description, conditions_id, dt_created, dt_modified, email, health_rating, ida, is_active, is_archived, is_commission, is_deleted, is_locked, line_increment, parent_id, parent_model, phone, price_level, priority, security_level, status, terms, total, uuid, version
    list_display = ("ida", "status", "email", "phone", "address_full", "attention", "is_active", "dt_created")
    list_filter = ("status", "is_active")
    search_fields = ("id", "ida")


@admin.register(InvoiceLine)
class InvoiceLineAdmin(SchemaLabelsAdminMixin, LineDisplayMixin, TransactionTotalsDisplayMixin, JSONBFieldsetMixin, admin.ModelAdmin):
    # Scalar fields: dt_created, dt_modified, health_rating, ida, is_active, is_archived, is_deleted, is_locked, line_number, price_level, security_level, status, uuid, version
    list_display = ("ida", "status", "health_rating", "is_locked", "line_number", "price_level", "is_active", "dt_created")
    list_filter = ("status", "is_active")
    search_fields = ("id", "ida")


##


##


##

@admin.register(WorkOrderLine)
class WorkOrderLineAdmin(SchemaLabelsAdminMixin, LineDisplayMixin, TransactionTotalsDisplayMixin, JSONBFieldsetMixin, admin.ModelAdmin):
    # Scalar fields: dt_created, dt_modified, health_rating, ida, is_active, is_archived, is_deleted, is_locked, line_number, price_level, security_level, status, uuid, version
    list_display = ("ida", "status", "health_rating", "is_locked", "line_number", "price_level", "is_active", "dt_created")
    list_filter = ("status", "is_active")
    search_fields = ("id", "ida")

    # Admin bulk actions used in tests
    actions = [
        'action_start',
        'action_mark_rework',
        'action_mark_done',
    ]

    def action_start(self, request, queryset):
        """Transition planned -> in_progress for selected lines."""
        updated = 0
        for ln in queryset:
            prev = ln.status or 'planned'
            try:
                ln.status = 'in_progress'
                ln.save()
                updated += 1
            except Exception as e:
                messages.warning(request, f"Cannot start line {ln.pk} from {prev}: {e}")
        if updated:
            messages.info(request, f"Started {updated} workorder line(s)")
    action_start.short_description = "Start selected lines"

    def action_mark_rework(self, request, queryset):
        """Attempt to mark selected lines as rework. Planned -> rework is invalid and should remain planned."""
        changed = 0
        for ln in queryset:
            prev = ln.status or 'planned'
            try:
                ln.status = 'rework'
                ln.save()
                changed += 1
            except Exception:
                # Keep previous status; notify
                messages.warning(request, f"Cannot mark rework for line {ln.pk} from {prev}")
        if changed:
            messages.info(request, f"Reworked {changed} workorder line(s)")
    action_mark_rework.short_description = "Mark selected lines as rework"

    def action_mark_done(self, request, queryset):
        """Mark selected lines as done."""
        updated = 0
        for ln in queryset:
            try:
                ln.status = 'done'
                ln.save()
                updated += 1
            except Exception as e:
                messages.warning(request, f"Cannot mark done for line {ln.pk}: {e}")
        if updated:
            messages.info(request, f"Marked done: {updated} workorder line(s)")
    action_mark_done.short_description = "Mark selected lines as done"


@admin.register(Order)
class OrderAdmin(SchemaLabelsAdminMixin, TransactionTotalsDisplayMixin, JSONBFieldsetMixin, admin.ModelAdmin):
    # Scalar fields: address_full, attention, balance, conditions_description, conditions_id, dt_created, dt_modified, email, health_rating, ida, is_active, is_archived, is_commission, is_deleted, is_locked, line_increment, parent_id, parent_model, phone, price_level, priority, security_level, status, terms, total, uuid, version
    list_display = ("ida", "status", "email", "phone", "address_full", "attention", "is_active", "dt_created")
    list_filter = ("status", "is_active")
    search_fields = ("id", "ida")


@admin.register(OrderLine)
class OrderLineAdmin(SchemaLabelsAdminMixin, LineDisplayMixin, TransactionTotalsDisplayMixin, JSONBFieldsetMixin, admin.ModelAdmin):
    # Scalar fields: dt_created, dt_modified, health_rating, ida, is_active, is_archived, is_deleted, is_locked, line_number, price_level, security_level, status, uuid, version
    list_display = ("ida", "status", "health_rating", "is_locked", "line_number", "price_level", "is_active", "dt_created")
    list_filter = ("status", "is_active")
    search_fields = ("id", "ida")


@admin.register(Purchase)
class PurchaseAdmin(SchemaLabelsAdminMixin, TransactionTotalsDisplayMixin, JSONBFieldsetMixin, admin.ModelAdmin):
    # Scalar fields: address_full, attention, balance, conditions_description, conditions_id, dt_created, dt_modified, email, health_rating, ida, is_active, is_archived, is_commission, is_deleted, is_locked, line_increment, parent_id, parent_model, phone, price_level, priority, security_level, status, terms, total, uuid, version
    list_display = ("ida", "status", "email", "phone", "address_full", "attention", "is_active", "dt_created")
    list_filter = ("status", "is_active")
    search_fields = ("id", "ida")


@admin.register(Project)
class ProjectAdmin(SchemaLabelsAdminMixin, TransactionTotalsDisplayMixin, JSONBFieldsetMixin, admin.ModelAdmin):
    # Scalar fields: attention, burndown, category, dt_created, dt_kanban, dt_modified, health_rating, contact_id, ida, intent, is_active, is_archived, is_deleted, is_locked, name, priority, profit, profit_velocity, security_level, situation, slug, status, uuid, version
    list_display = ("ida", "name", "status", "attention", "burndown", "category", "is_active", "dt_created")
    list_filter = ("status", "priority")
    search_fields = ("id", "name", "intent", "slug")
    details_fieldset_title = "Project Details"

@admin.register(PurchaseLine)
class PurchaseLineAdmin(SchemaLabelsAdminMixin, LineDisplayMixin, TransactionTotalsDisplayMixin, JSONBFieldsetMixin, admin.ModelAdmin):
    # Scalar fields: dt_created, dt_modified, health_rating, ida, is_active, is_archived, is_deleted, is_locked, line_number, price_level, security_level, status, uuid, version
    list_display = ("ida", "status", "health_rating", "is_locked", "line_number", "price_level", "is_active", "dt_created")
    list_filter = ("status", "is_active")
    search_fields = ("id", "ida")


@admin.register(Proposal)
class ProposalAdmin(SchemaLabelsAdminMixin, TransactionTotalsDisplayMixin, JSONBFieldsetMixin, admin.ModelAdmin):
    # Scalar fields: address_full, attention, balance, conditions_description, conditions_id, dt_created, dt_modified, email, health_rating, ida, is_active, is_archived, is_commission, is_deleted, is_locked, line_increment, parent_id, parent_model, phone, price_level, priority, security_level, status, terms, total, uuid, version
    list_display = ("ida", "status", "email", "phone", "address_full", "attention", "is_active", "dt_created")
    list_filter = ("status", "is_active")
    search_fields = ("id", "ida")


@admin.register(ProposalLine)
class ProposalLineAdmin(SchemaLabelsAdminMixin, LineDisplayMixin, TransactionTotalsDisplayMixin, JSONBFieldsetMixin, admin.ModelAdmin):
    # Scalar fields: dt_created, dt_modified, health_rating, ida, is_active, is_archived, is_deleted, is_locked, line_number, price_level, security_level, status, uuid, version
    list_display = ("ida", "status", "health_rating", "is_locked", "line_number", "price_level", "is_active", "dt_created")
    list_filter = ("status", "is_active")
    search_fields = ("id", "ida")


@admin.register(Requisition)
class RequisitionAdmin(SchemaLabelsAdminMixin, TransactionTotalsDisplayMixin, JSONBFieldsetMixin, admin.ModelAdmin):
    # Scalar fields: dt_created, dt_modified, health_rating, ida, is_active, is_archived, is_deleted, is_locked, name, purpose, security_level, status, uuid, version
    list_display = ("ida", "name", "status", "health_rating", "is_locked", "purpose", "is_active", "dt_created")
    list_filter = ("status", "is_active")
    search_fields = ("id", "ida", "name")


@admin.register(RequisitionLine)
class RequisitionLineAdmin(SchemaLabelsAdminMixin, LineDisplayMixin, TransactionTotalsDisplayMixin, JSONBFieldsetMixin, admin.ModelAdmin):
    # Scalar fields: dt_created, dt_modified, health_rating, ida, is_active, is_archived, is_deleted, is_locked, line_number, price_level, security_level, status, uuid, version
    list_display = ("ida", "status", "health_rating", "is_locked", "line_number", "price_level", "is_active", "dt_created")
    list_filter = ("status", "is_active")
    search_fields = ("id", "ida")


@admin.register(Receipt)
class ReceiptAdmin(SchemaLabelsAdminMixin, TransactionTotalsDisplayMixin, JSONBFieldsetMixin, admin.ModelAdmin):
    # Scalar fields: dt_created, dt_modified, dt_received, health_rating, ida, is_active, is_archived, is_deleted, is_locked, notes, security_level, source_type, uuid, version
    list_display = ("ida", "dt_received", "health_rating", "is_locked", "notes", "security_level", "is_active", "dt_created")
    list_filter = ("is_active",)
    search_fields = ("id", "ida")


@admin.register(WorkOrder)
class WorkOrderAdmin(SchemaLabelsAdminMixin, TransactionTotalsDisplayMixin, JSONBFieldsetMixin, admin.ModelAdmin):
    # Scalar fields: address_full, attention, balance, conditions_description, conditions_id, dt_created, dt_modified, email, health_rating, ida, is_active, is_archived, is_commission, is_deleted, is_locked, line_increment, parent_id, parent_model, phone, price_level, priority, security_level, status, terms, total, uuid, version
    list_display = ("ida", "status", "email", "phone", "address_full", "attention", "is_active", "dt_created")
    list_filter = ("status", "is_active")
    search_fields = ("id", "ida")


@admin.register(Payment)
class PaymentAdmin(SchemaLabelsAdminMixin, JSONBFieldsetMixin, admin.ModelAdmin):
    # Scalar fields: amount, dt_created, dt_modified, dt_payment, dt_processed, dt_reconciliation, fee_amount, gateway, health_rating, gateway_payment_intent_id, gateway_transaction_id, ida, is_active, is_archived, is_deleted, is_locked, notes, reconciled, reference_number, security_level, status, uuid, version
    list_display = ("ida", "status", "amount", "dt_payment", "dt_processed", "dt_reconciliation", "is_active", "dt_created")
    list_filter = ("status", "gateway", "reconciled", "is_active")
    search_fields = ("reference_number", "gateway_transaction_id", "gateway_payment_intent_id", "notes", "ida")
    readonly_fields = ("uuid", "dt_created", "dt_modified")


@admin.register(PaymentMethod)
class PaymentMethodAdmin(ScalarFirstFieldsetMixin, SchemaLabelsAdminMixin, admin.ModelAdmin):
    # Scalar fields: description, dt_created, dt_modified, health_rating, ida, is_active, is_archived, is_deleted, is_locked, name, security_level, uuid, version
    list_display = ("ida", "name", "description", "health_rating", "is_locked", "security_level", "is_active", "dt_created")
    list_filter = ("is_active",)
    search_fields = ("name", "description")


@admin.register(PaymentTerm)
class PaymentTermAdmin(ScalarFirstFieldsetMixin, SchemaLabelsAdminMixin, admin.ModelAdmin):
    # Scalar fields: days, description, dt_created, dt_modified, health_rating, ida, is_active, is_archived, is_deleted, is_locked, name, security_level, uuid, version
    list_display = ("ida", "name", "description", "days", "health_rating", "is_locked", "is_active", "dt_created")
    list_filter = ("is_active",)
    search_fields = ("name", "description")


@admin.register(PaymentApplication)
class PaymentApplicationAdmin(SchemaLabelsAdminMixin, JSONBFieldsetMixin, admin.ModelAdmin):
    # Scalar fields: amount, applied_at, dt_created, dt_modified, health_rating, ida, is_active, is_archived, is_deleted, is_locked, notes, security_level, uuid, version
    list_display = ("ida", "amount", "applied_at", "health_rating", "is_locked", "notes", "is_active", "dt_created")
    list_filter = ("is_active",)
    search_fields = ("notes", "ida")
    readonly_fields = ("uuid", "dt_created", "dt_modified")
