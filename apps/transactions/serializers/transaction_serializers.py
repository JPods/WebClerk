from rest_framework import serializers

from common.base_serializers import RoleAwareModelSerializer

from apps.transactions.models import (
    Proposal, ProposalLine, Order, OrderLine, Purchase, PurchaseLine, Invoice, Payment, PaymentApplication
)
from apps.core.models import Contact
from apps.orgs.models import OrgBase


# system fields inherited from BaseModel (read-only)
_BASE_RO = [
    'id', 'uuid', 'dt_created', 'dt_modified', 'version',
    'is_deleted', 'is_archived', 'metadata', 'refs', 'prefs',
    'actions', 'comments', 'health_rating',
]


class ProposalLineSerializer(RoleAwareModelSerializer):
    """Serializer aligned with ProposalLine schema."""

    class Meta:
        model = ProposalLine
        fields = [
            'id', 'uuid', 'ida', 'dt_created', 'dt_modified', 'version',
            'is_active', 'security_level', 'is_deleted', 'is_archived',
            'metadata', 'refs', 'prefs', 'actions', 'comments', 'health_rating',
            'price_level', 'status', 'item_fk', 'item',
            'quantity', 'cost', 'tax', 'physical', 'price', 'proposal',
        ]
        read_only_fields = _BASE_RO


class ProposalSerializer(RoleAwareModelSerializer):
    """Serializer for Proposal transactions.

    totals JSON envelope is the source of truth for all computed values
    (total, margin, margin_pc, balance, etc.). No flattening — React
    reads totals.total, totals.margin, totals.margin_pc directly.
    """

    line_count = serializers.IntegerField(read_only=True)
    customer_name = serializers.SerializerMethodField(read_only=True)
    vendor_name = serializers.SerializerMethodField(read_only=True)
    lines = ProposalLineSerializer(many=True, read_only=True)

    class Meta:
        model = Proposal
        fields = [
            'id', 'uuid', 'ida', 'status', 'customer_id', 'vendor_id',
            'customer_name', 'vendor_name',
            'cost', 'sell', 'totals', 'total', 'balance',
            'finance', 'flow', 'source', 'action', 'refs', 'prefs', 'metadata',
            'line_count', 'lines',
            'dt_created', 'dt_modified', 'version'
        ]
        read_only_fields = [
            'id', 'uuid', 'dt_created', 'dt_modified', 'version', 'customer_name',
            'vendor_name', 'totals', 'total', 'balance', 'line_count', 'lines'
        ]

    def get_customer_name(self, obj):
        if obj.customer_id:
            try:
                org = OrgBase.objects.get(id=obj.customer_id)
                return org.display_name
            except OrgBase.DoesNotExist:
                return f"Org #{obj.customer_id}"
        return None

    def get_vendor_name(self, obj):
        if obj.vendor_id:
            try:
                org = OrgBase.objects.get(id=obj.vendor_id)
                return org.display_name
            except OrgBase.DoesNotExist:
                return f"Org #{obj.vendor_id}"
        return None

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if hasattr(instance, 'lines'):
            try:
                data['line_count'] = instance.lines.count()
            except Exception:
                data['line_count'] = len(data.get('lines', []) or [])
        return data

    def validate_status(self, value):
        valid_statuses = ['planned', 'sent', 'accepted', 'rejected', 'cancelled']
        if value not in valid_statuses:
            raise serializers.ValidationError(f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
        return value

    def validate_customer_id(self, value):
        if value and value > 0:
            try:
                OrgBase.objects.get(id=value)
            except OrgBase.DoesNotExist:
                raise serializers.ValidationError("Customer organization does not exist.")
        return value

    def validate_vendor_id(self, value):
        if value and value > 0:
            try:
                OrgBase.objects.get(id=value)
            except OrgBase.DoesNotExist:
                raise serializers.ValidationError("Vendor organization does not exist.")
        return value

    def validate(self, data):
        if data.get('customer_id') and data.get('vendor_id') and data['customer_id'] == data['vendor_id']:
            raise serializers.ValidationError("Customer and vendor cannot be the same entity.")
        return data


class OrderLineSerializer(RoleAwareModelSerializer):
    """Serializer aligned with OrderLine schema."""

    class Meta:
        model = OrderLine
        fields = [
            'id', 'uuid', 'ida', 'dt_created', 'dt_modified', 'version',
            'is_active', 'security_level', 'is_deleted', 'is_archived',
            'metadata', 'refs', 'prefs', 'actions', 'comments', 'health_rating',
            'price_level', 'status', 'item_fk', 'item',
            'quantity', 'cost', 'tax', 'physical', 'price', 'order',
        ]
        read_only_fields = _BASE_RO


class PurchaseLineSerializer(RoleAwareModelSerializer):
    """Serializer aligned with PurchaseLine schema."""

    class Meta:
        model = PurchaseLine
        fields = [
            'id', 'uuid', 'ida', 'dt_created', 'dt_modified', 'version',
            'is_active', 'security_level', 'is_deleted', 'is_archived',
            'metadata', 'refs', 'prefs', 'actions', 'comments', 'health_rating',
            'price_level', 'status', 'item_fk', 'item',
            'quantity', 'cost', 'tax', 'physical', 'purchase',
        ]
        read_only_fields = _BASE_RO


class OrderSerializer(RoleAwareModelSerializer):
    """Serializer for Order transactions.

    totals JSON envelope is the source of truth for all computed values.
    No flattening — React reads totals.total, totals.margin, totals.margin_pc.
    """

    line_count = serializers.IntegerField(read_only=True)
    customer_name = serializers.SerializerMethodField(read_only=True)
    vendor_name = serializers.SerializerMethodField(read_only=True)
    lines = OrderLineSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'uuid', 'ida', 'status', 'priority', 'price_level',
            'customer_id', 'manufacturer_id', 'vendor_id',
            'cost', 'sell', 'totals', 'total', 'balance',
            'finance', 'flow', 'source', 'action', 'refs', 'prefs', 'metadata',
            'line_count', 'customer_name', 'vendor_name', 'lines',
            'dt_created', 'dt_modified', 'version'
        ]
        read_only_fields = ['id', 'uuid', 'dt_created', 'dt_modified', 'version',
            'totals', 'total', 'balance', 'line_count', 'customer_name', 'vendor_name', 'lines']

    def get_customer_name(self, obj):
        """Get customer name from OrgBase model."""
        if obj.customer_id:
            try:
                org = OrgBase.objects.get(id=obj.customer_id)
                return org.display_name
            except OrgBase.DoesNotExist:
                return f"Org #{obj.customer_id}"
        return None

    def get_vendor_name(self, obj):
        """Get vendor name from OrgBase model."""
        if obj.vendor_id:
            try:
                org = OrgBase.objects.get(id=obj.vendor_id)
                return org.display_name
            except OrgBase.DoesNotExist:
                return f"Org #{obj.vendor_id}"
        return None

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if hasattr(instance, 'lines'):
            data['line_count'] = instance.lines.count()
        return data

    def validate_status(self, value):
        """Validate status transitions."""
        valid_statuses = ['planned', 'released', 'in_progress', 'hold', 'complete', 'canceled']
        if value not in valid_statuses:
            raise serializers.ValidationError(f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
        return value

    def validate_customer_id(self, value):
        """Validate customer exists."""
        if value and value > 0:
            try:
                OrgBase.objects.get(id=value)
            except OrgBase.DoesNotExist:
                raise serializers.ValidationError("Customer organization does not exist.")
        return value

    def validate_vendor_id(self, value):
        """Validate vendor exists."""
        if value and value > 0:
            try:
                OrgBase.objects.get(id=value)
            except OrgBase.DoesNotExist:
                raise serializers.ValidationError("Vendor organization does not exist.")
        return value

    def validate(self, data):
        """Cross-field validation."""
        if data.get('customer_id') and data.get('vendor_id') and data['customer_id'] == data['vendor_id']:
            raise serializers.ValidationError("Customer and vendor cannot be the same entity.")

        return data


class PurchaseSerializer(RoleAwareModelSerializer):
    """Serializer for Purchase transactions.

    totals JSON envelope is the source of truth for all computed values.
    No flattening — React reads totals.total, totals.cost, totals.balance.
    """

    line_count = serializers.IntegerField(read_only=True)
    customer_name = serializers.SerializerMethodField(read_only=True)
    vendor_name = serializers.SerializerMethodField(read_only=True)
    lines = PurchaseLineSerializer(many=True, read_only=True)

    class Meta:
        model = Purchase
        fields = [
            'id', 'uuid', 'ida', 'status', 'priority', 'price_level',
            'customer_id', 'manufacturer_id', 'vendor_id',
            'customer_name', 'vendor_name',
            'cost', 'sell', 'totals', 'total', 'balance',
            'finance', 'flow', 'source', 'action', 'refs', 'metadata',
            'line_count', 'lines',
            'dt_created', 'dt_modified', 'version'
        ]
        read_only_fields = ['id', 'uuid', 'dt_created', 'dt_modified', 'version',
            'totals', 'total', 'balance', 'line_count', 'customer_name', 'vendor_name', 'lines']

    def get_customer_name(self, obj):
        """Get customer name from Contact model."""
        if obj.customer_id:
            try:
                contact = Contact.objects.get(id=obj.customer_id)
                return f"{contact.name_first} {contact.name_last}".strip()
            except Contact.DoesNotExist:
                return f"Contact #{obj.customer_id}"
        return None

    def get_vendor_name(self, obj):
        """Get vendor name from Contact model."""
        if obj.vendor_id:
            try:
                contact = Contact.objects.get(id=obj.vendor_id)
                return f"{contact.name_first} {contact.name_last}".strip()
            except Contact.DoesNotExist:
                return f"Contact #{obj.vendor_id}"
        return None

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if hasattr(instance, 'purchaseline_set'):
            data['line_count'] = instance.purchaseline_set.count()
        return data


class InvoiceSerializer(RoleAwareModelSerializer):
    """Serializer for Invoice transactions.

    totals JSON envelope is the source of truth for all computed values.
    No flattening — React reads totals.total, totals.balance, totals.margin.
    """

    class Meta:
        model = Invoice
        fields = [
            'id', 'uuid', 'ida', 'status', 'customer_id', 'vendor_id',
            'cost', 'sell', 'totals', 'total', 'balance',
            'finance', 'flow', 'source', 'action',
            'dt_created', 'dt_modified', 'version'
        ]
        read_only_fields = ['id', 'uuid', 'dt_created', 'dt_modified', 'version',
            'totals', 'total', 'balance']


class PaymentSerializer(RoleAwareModelSerializer):
    """Serializer for Payment transactions."""

    class Meta:
        model = Payment
        fields = [
            'id', 'uuid', 'type', 'category', 'amount', 'dt_payment',
            'method', 'payment_term_id',
            'reference_number', 'notes', 'gateway', 'id_gateway_transaction',
            'id_gateway_payment_intent', 'status', 'gateway_response',
            'dt_processed', 'reconciled', 'dt_reconciliation', 'fee_amount',
            'contact_id', 'customer_id', 'vendor_id', 'invoice_id', 'purchase_id',
            'dt_created', 'dt_modified', 'version',
            'refs', 'metadata', 'comments', 'is_active',
        ]
        read_only_fields = ['id', 'uuid', 'dt_created', 'dt_modified', 'version']


class PaymentApplicationSerializer(serializers.ModelSerializer):
    """Serializer for Payment Application records."""

    class Meta:
        model = PaymentApplication
        fields = [
            'id', 'payment', 'invoice', 'amount', 'applied_at', 'notes',
            'dt_created', 'dt_modified', 'version'
        ]
        read_only_fields = ['id', 'dt_created', 'dt_modified', 'version']


class StatementLineSerializer(RoleAwareModelSerializer):
    """Serializer for StatementLine — bank/card statement import staging."""

    class Meta:
        from apps.transactions.models.statement_line import StatementLine as SLModel
        model = SLModel
        fields = [
            'id', 'uuid', 'ida',
            'dt_transaction', 'description', 'amount', 'raw_text',
            'source', 'statement_date', 'batch_id',
            'classification', 'category', 'merchant', 'ledger',
            'contact_id', 'vendor_id',
            'promoted', 'payment_id',
            'dt_created', 'dt_modified', 'version',
            'is_active', 'refs', 'metadata', 'prefs', 'comments',
        ]
        read_only_fields = ['id', 'uuid', 'dt_created', 'dt_modified', 'version']


__all__ = [
    'ProposalSerializer',
    'ProposalLineSerializer',
    'OrderSerializer',
    'OrderLineSerializer',
    'PurchaseSerializer',
    'PurchaseLineSerializer',
    'InvoiceSerializer',
    'PaymentSerializer',
    'PaymentApplicationSerializer',
    'StatementLineSerializer',
]