from rest_framework import serializers
from decimal import Decimal

from common.base_serializers import RoleAwareModelSerializer

from apps.transactions.models import (
    Proposal, ProposalLine, Order, OrderLine, Purchase, PurchaseLine, Invoice, Payment, PaymentApplication
)
from apps.core.models import Contact


class ProposalLineSerializer(RoleAwareModelSerializer):
    """Serializer aligned with ProposalLine schema."""

    class Meta:
        model = ProposalLine
        fields = '__all__'
        read_only_fields = ['id', 'dt_created', 'dt_modified', 'version']


class ProposalSerializer(RoleAwareModelSerializer):
    """Serializer for Proposal transactions."""

    total_amount = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    line_count = serializers.IntegerField(read_only=True)
    customer_name = serializers.SerializerMethodField(read_only=True)
    vendor_name = serializers.SerializerMethodField(read_only=True)
    margin_amount = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    margin_percentage = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    lines = ProposalLineSerializer(many=True, read_only=True)

    class Meta:
        model = Proposal
        fields = [
            'id', 'uuid', 'ida', 'status', 'customer_id', 'vendor_id',
            'customer_name', 'vendor_name',
            'cost', 'sell', 'finance', 'flow', 'source', 'action', 'refs', 'prefs', 'metadata',
            'total_amount', 'line_count', 'margin_amount', 'margin_percentage', 'lines',
            'dt_created', 'dt_modified', 'version'
        ]
        read_only_fields = [
            'id', 'uuid', 'dt_created', 'dt_modified', 'version', 'customer_name',
            'vendor_name', 'total_amount', 'line_count', 'margin_amount', 'margin_percentage', 'lines'
        ]

    def get_customer_name(self, obj):
        if obj.customer_id:
            try:
                contact = Contact.objects.get(id=obj.customer_id)
                return f"{contact.name_first} {contact.name_last}".strip()
            except Contact.DoesNotExist:
                return f"Contact #{obj.customer_id}"
        return None

    def get_vendor_name(self, obj):
        if obj.vendor_id:
            try:
                contact = Contact.objects.get(id=obj.vendor_id)
                return f"{contact.name_first} {contact.name_last}".strip()
            except Contact.DoesNotExist:
                return f"Contact #{obj.vendor_id}"
        return None

    def to_representation(self, instance):
        data = super().to_representation(instance)

        if hasattr(instance, 'sell') and instance.sell:
            sell_data = instance.sell or {}
            sell_total = Decimal(str(sell_data.get('total', 0) or 0))
            data['total_amount'] = str(sell_total)

        if hasattr(instance, 'lines'):
            try:
                data['line_count'] = instance.lines.count()
            except Exception:
                data['line_count'] = len(data.get('lines', []) or [])

        total_sell = Decimal(str(data.get('total_amount', 0) or 0))
        total_cost = Decimal('0')
        if hasattr(instance, 'cost') and instance.cost:
            total_cost = Decimal(str(instance.cost.get('total', 0) or 0))

        margin_amount = (total_sell - total_cost).quantize(Decimal('0.01'))
        data['margin_amount'] = str(margin_amount)

        if total_sell:
            margin_percentage = ((margin_amount / total_sell) * Decimal('100')).quantize(Decimal('0.01'))
            data['margin_percentage'] = str(margin_percentage)
        else:
            data['margin_percentage'] = str(Decimal('0.00'))

        return data

    def validate_status(self, value):
        valid_statuses = ['planned', 'sent', 'accepted', 'rejected', 'cancelled']
        if value not in valid_statuses:
            raise serializers.ValidationError(f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
        return value

    def validate_customer_id(self, value):
        if value and value > 0:
            try:
                Contact.objects.get(id=value)
            except Contact.DoesNotExist:
                raise serializers.ValidationError("Customer contact does not exist.")
        return value

    def validate_vendor_id(self, value):
        if value and value > 0:
            try:
                Contact.objects.get(id=value)
            except Contact.DoesNotExist:
                raise serializers.ValidationError("Vendor contact does not exist.")
        return value

    def validate(self, data):
        if data.get('customer_id') and data.get('vendor_id') and data['customer_id'] == data['vendor_id']:
            raise serializers.ValidationError("Customer and vendor cannot be the same entity.")
        return data


class OrderLineSerializer(RoleAwareModelSerializer):
    """Serializer aligned with OrderLine schema."""

    class Meta:
        model = OrderLine
        fields = '__all__'
        read_only_fields = ['id', 'dt_created', 'dt_modified', 'version']


class PurchaseLineSerializer(RoleAwareModelSerializer):
    """Serializer aligned with PurchaseLine schema."""

    class Meta:
        model = PurchaseLine
        fields = '__all__'
        read_only_fields = ['id', 'dt_created', 'dt_modified', 'version']


class OrderSerializer(RoleAwareModelSerializer):
    """Serializer for Order transactions."""

    total_amount = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    line_count = serializers.IntegerField(read_only=True)
    customer_name = serializers.SerializerMethodField(read_only=True)
    vendor_name = serializers.SerializerMethodField(read_only=True)
    margin_amount = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    margin_percentage = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    lines = OrderLineSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'uuid', 'ida', 'status', 'priority', 'price_level',
            'customer_id', 'manufacturer_id', 'vendor_id',
            'cost', 'sell', 'finance', 'flow', 'source', 'action', 'refs', 'prefs', 'metadata',
            'total_amount', 'line_count', 'customer_name', 'vendor_name', 'margin_amount', 'margin_percentage', 'lines',
            'dt_created', 'dt_modified', 'version'
        ]
        read_only_fields = ['id', 'uuid', 'dt_created', 'dt_modified', 'version', 'total_amount', 'line_count', 'customer_name', 'vendor_name', 'margin_amount', 'margin_percentage', 'lines']

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
        """Add computed fields to the representation."""
        data = super().to_representation(instance)

        # Add computed totals
        if hasattr(instance, 'sell') and instance.sell:
            sell_data = instance.sell
            data['total_amount'] = sell_data.get('total', 0)

        # Add line count
        if hasattr(instance, 'lines'):
            data['line_count'] = instance.lines.count()

        # Add margin calculations
        total_sell = data.get('total_amount', 0) or 0
        total_cost = 0
        if hasattr(instance, 'cost') and instance.cost:
            total_cost = instance.cost.get('total', 0) or 0

        data['margin_amount'] = float(Decimal(str(total_sell)) - Decimal(str(total_cost)))
        if total_sell > 0:
            data['margin_percentage'] = float((Decimal(str(data['margin_amount'])) / Decimal(str(total_sell))) * 100)
        else:
            data['margin_percentage'] = 0

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
                Contact.objects.get(id=value)
            except Contact.DoesNotExist:
                raise serializers.ValidationError("Customer contact does not exist.")
        return value

    def validate_vendor_id(self, value):
        """Validate vendor exists."""
        if value and value > 0:
            try:
                Contact.objects.get(id=value)
            except Contact.DoesNotExist:
                raise serializers.ValidationError("Vendor contact does not exist.")
        return value

    def validate(self, data):
        """Cross-field validation."""
        if data.get('customer_id') and data.get('vendor_id') and data['customer_id'] == data['vendor_id']:
            raise serializers.ValidationError("Customer and vendor cannot be the same entity.")

        return data


class PurchaseSerializer(RoleAwareModelSerializer):
    """Serializer for Purchase transactions."""

    total_amount = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
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
            'cost', 'sell', 'finance', 'flow', 'source', 'action', 'refs', 'metadata',
            'total_amount', 'line_count', 'lines',
            'dt_created', 'dt_modified', 'version'
        ]
        read_only_fields = ['id', 'uuid', 'dt_created', 'dt_modified', 'version', 'total_amount', 'line_count', 'customer_name', 'vendor_name', 'lines']

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
        """Add computed fields to the representation."""
        data = super().to_representation(instance)

        # Add computed totals
        if hasattr(instance, 'cost') and instance.cost:
            cost_data = instance.cost
            data['total_amount'] = cost_data.get('total', 0)

        # Add line count
        if hasattr(instance, 'purchaseline_set'):
            data['line_count'] = instance.purchaseline_set.count()

        return data


class InvoiceSerializer(RoleAwareModelSerializer):
    """Serializer for Invoice transactions."""

    class Meta:
        model = Invoice
        fields = [
            'id', 'uuid', 'ida', 'status', 'customer_id', 'vendor_id',
            'cost', 'sell', 'finance', 'flow', 'source', 'action',
            'dt_created', 'dt_modified', 'version'
        ]
        read_only_fields = ['id', 'uuid', 'dt_created', 'dt_modified', 'version']


class PaymentSerializer(RoleAwareModelSerializer):
    """Serializer for Payment transactions."""

    class Meta:
        model = Payment
        fields = [
            'id', 'uuid', 'amount', 'dt_payment', 'paymentmethod_id', 'paymentterm_id',
            'reference_number', 'notes', 'gateway', 'id_gateway_transaction',
            'id_gateway_payment_intent', 'status', 'gateway_response',
            'dt_processed', 'reconciled', 'dt_reconciliation', 'fee_amount',
            'contact_id', 'invoice_id', 'dt_created', 'dt_modified', 'version'
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
]