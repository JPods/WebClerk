from rest_framework import serializers
from common.base_serializers import RoleAwareModelSerializer
from decimal import Decimal

from apps.transactions.models import (
    Proposal, ProposalLine, SalesOrder, PurchaseOrder, Invoice, Payment, PaymentApplication
)
from apps.core.models import Contact


class ProposalSerializer(RoleAwareModelSerializer):
    """Serializer for Proposal transactions."""

    proposal_no = serializers.CharField(read_only=True)
    total_amount = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    line_count = serializers.IntegerField(read_only=True)
    customer_name = serializers.SerializerMethodField(read_only=True)
    vendor_name = serializers.SerializerMethodField(read_only=True)
    margin_amount = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    margin_percentage = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    lines = ProposalLineSerializer(many=True, read_only=True, source='proposalline_set')

    class Meta:
        model = Proposal
        fields = [
            'id', 'uuid', 'ida', 'proposal_no', 'status', 'id_customer', 'id_vendor',
            'customer_name', 'vendor_name',
            'cost', 'sell', 'finance', 'flow', 'source', 'action',
            'total_amount', 'line_count', 'margin_amount', 'margin_percentage', 'lines',
            'dt_created', 'dt_modified', 'version'
        ]
        read_only_fields = ['id', 'uuid', 'dt_created', 'dt_modified', 'version', 'proposal_no', 'total_amount', 'line_count', 'customer_name', 'vendor_name', 'margin_amount', 'margin_percentage', 'lines']

    def get_customer_name(self, obj):
        """Get customer name from Contact model."""
        if obj.id_customer:
            try:
                contact = Contact.objects.get(id=obj.id_customer)
                return f"{contact.name_first} {contact.name_last}".strip()
            except Contact.DoesNotExist:
                return f"Contact #{obj.id_customer}"
        return None

    def get_vendor_name(self, obj):
        """Get vendor name from Contact model."""
        if obj.id_vendor:
            try:
                contact = Contact.objects.get(id=obj.id_vendor)
                return f"{contact.name_first} {contact.name_last}".strip()
            except Contact.DoesNotExist:
                return f"Contact #{obj.id_vendor}"
        return None

    def to_representation(self, instance):
        """Add computed fields to the representation."""
        data = super().to_representation(instance)

        # Add computed totals
        if hasattr(instance, 'sell') and instance.sell:
            sell_data = instance.sell
            data['total_amount'] = sell_data.get('total', 0)

        # Add line count
        if hasattr(instance, 'proposalline_set'):
            data['line_count'] = instance.proposalline_set.count()

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
        valid_statuses = ['planned', 'sent', 'accepted', 'rejected', 'cancelled']
        if value not in valid_statuses:
            raise serializers.ValidationError(f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
        return value

    def validate_id_customer(self, value):
        """Validate customer exists."""
        if value and value > 0:
            try:
                Contact.objects.get(id=value)
            except Contact.DoesNotExist:
                raise serializers.ValidationError("Customer contact does not exist.")
        return value

    def validate_id_vendor(self, value):
        """Validate vendor exists."""
        if value and value > 0:
            try:
                Contact.objects.get(id=value)
            except Contact.DoesNotExist:
                raise serializers.ValidationError("Vendor contact does not exist.")
        return value

    def validate(self, data):
        """Cross-field validation."""
        if data.get('id_customer') and data.get('id_vendor') and data['id_customer'] == data['id_vendor']:
            raise serializers.ValidationError("Customer and vendor cannot be the same entity.")

        # Validate status transitions
        instance = self.instance
        if instance and 'status' in data:
            old_status = instance.status
            new_status = data['status']
            valid_transitions = {
                'planned': ['sent', 'cancelled'],
                'sent': ['accepted', 'rejected', 'cancelled'],
                'accepted': [],  # Final state
                'rejected': ['sent'],  # Can resend
                'cancelled': [],  # Final state
            }
            if new_status not in valid_transitions.get(old_status, []):
                raise serializers.ValidationError(f"Invalid status transition from {old_status} to {new_status}.")

        return data


class ProposalLineSerializer(RoleAwareModelSerializer):
    """Serializer for Proposal Line items."""

    extended_price = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    item_name = serializers.CharField(read_only=True)
    unit_cost = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    line_margin = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)

    class Meta:
        model = ProposalLine
        fields = [
            'id', 'parent', 'item_id', 'description', 'quantity', 'price',
            'discount_amount', 'extended_price', 'item_name', 'unit_cost', 'line_margin',
            'dt_created', 'dt_modified', 'version'
        ]
        read_only_fields = ['id', 'dt_created', 'dt_modified', 'version', 'extended_price', 'item_name', 'unit_cost', 'line_margin']

    def to_representation(self, instance):
        """Add computed fields to the representation."""
        data = super().to_representation(instance)

        # Calculate extended price
        quantity = Decimal(str(instance.quantity or 0))
        price = Decimal(str(instance.price.get('sell', 0) if instance.price else 0))
        discount = Decimal(str(instance.discount_amount or 0))
        data['extended_price'] = float((quantity * price) - discount)

        # Calculate unit cost and line margin
        unit_cost = Decimal(str(instance.price.get('cost', 0) if instance.price else 0))
        data['unit_cost'] = float(unit_cost)
        sell_price = price
        data['line_margin'] = float((sell_price - unit_cost) * quantity - discount)

        # Add item name if available
        if hasattr(instance, 'item') and instance.item:
            data['item_name'] = instance.item.name
        else:
            data['item_name'] = instance.description or 'Unknown Item'

        return data

    def validate_quantity(self, value):
        """Validate quantity is positive."""
        if value <= 0:
            raise serializers.ValidationError("Quantity must be greater than zero.")
        return value

    def validate_discount_amount(self, value):
        """Validate discount is not negative."""
        if value < 0:
            raise serializers.ValidationError("Discount amount cannot be negative.")
        return value

    def validate_price(self, value):
        """Validate price structure."""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Price must be a dictionary with sell and cost keys.")
        if 'sell' not in value or value['sell'] < 0:
            raise serializers.ValidationError("Sell price must be provided and non-negative.")
        if 'cost' not in value and value.get('cost', 0) < 0:
            raise serializers.ValidationError("Cost price must be non-negative.")
        return value

    def validate(self, data):
        """Cross-field validation."""
        if data.get('item_id') and not data.get('description'):
            # Could auto-populate description from item, but for now just validate
            pass

        # Validate discount doesn't exceed extended price
        quantity = data.get('quantity', 1)
        price = data.get('price', {}).get('sell', 0)
        discount = data.get('discount_amount', 0)
        extended = quantity * price
        if discount > extended:
            raise serializers.ValidationError("Discount amount cannot exceed the extended price.")

        return data


class SalesOrderSerializer(RoleAwareModelSerializer):
    """Serializer for Sales Order transactions."""

    order_no = serializers.CharField(read_only=True)

    class Meta:
        model = SalesOrder
        fields = [
            'id', 'uuid', 'ida', 'status', 'priority', 'price_level',
            'id_customer', 'id_manufacturer', 'id_vendor',
            'order_no', 'cost', 'sell', 'finance', 'flow', 'source', 'action',
            'dt_created', 'dt_modified', 'version'
        ]
        read_only_fields = ['id', 'uuid', 'dt_created', 'dt_modified', 'version']


class PurchaseOrderSerializer(RoleAwareModelSerializer):
    """Serializer for Purchase Order transactions."""

    po_no = serializers.CharField(read_only=True)

    class Meta:
        model = PurchaseOrder
        fields = [
            'id', 'uuid', 'ida', 'status', 'priority', 'price_level',
            'id_customer', 'id_manufacturer', 'id_vendor',
            'po_no', 'cost', 'sell', 'finance', 'flow', 'source', 'action',
            'dt_created', 'dt_modified', 'version'
        ]
        read_only_fields = ['id', 'uuid', 'dt_created', 'dt_modified', 'version']


class InvoiceSerializer(RoleAwareModelSerializer):
    """Serializer for Invoice transactions."""

    class Meta:
        model = Invoice
        fields = [
            'id', 'uuid', 'ida', 'status', 'id_customer', 'id_vendor',
            'cost', 'sell', 'finance', 'flow', 'source', 'action',
            'dt_created', 'dt_modified', 'version'
        ]
        read_only_fields = ['id', 'uuid', 'dt_created', 'dt_modified', 'version']


class PaymentSerializer(RoleAwareModelSerializer):
    """Serializer for Payment transactions."""

    class Meta:
        model = Payment
        fields = [
            'id', 'uuid', 'amount', 'payment_date', 'payment_method', 'payment_term',
            'reference_number', 'notes', 'gateway', 'gateway_transaction_id',
            'gateway_payment_intent_id', 'status', 'gateway_response',
            'processed_at', 'reconciled', 'reconciliation_date', 'fee_amount',
            'contact', 'invoice', 'dt_created', 'dt_modified', 'version'
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
    'SalesOrderSerializer',
    'PurchaseOrderSerializer',
    'InvoiceSerializer',
    'PaymentSerializer',
    'PaymentApplicationSerializer',
]