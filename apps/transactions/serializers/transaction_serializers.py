from rest_framework import serializers
from common.base_serializers import RoleAwareModelSerializer

from apps.transactions.models import (
    Proposal, SalesOrder, PurchaseOrder, Invoice, Payment, PaymentApplication
)


class ProposalSerializer(RoleAwareModelSerializer):
    """Serializer for Proposal transactions."""

    class Meta:
        model = Proposal
        fields = [
            'id', 'uuid', 'ida', 'status', 'id_customer', 'id_vendor',
            'cost', 'sell', 'finance', 'flow', 'source', 'action',
            'dt_created', 'dt_modified', 'version'
        ]
        read_only_fields = ['id', 'uuid', 'dt_created', 'dt_modified', 'version']


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
    'SalesOrderSerializer',
    'PurchaseOrderSerializer',
    'InvoiceSerializer',
    'PaymentSerializer',
    'PaymentApplicationSerializer',
]