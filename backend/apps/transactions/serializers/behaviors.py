"""Shared serializer behaviors for transaction types.

Each function is a standalone validator or field exposer that works on any
TransactionBaseModel. Serializers call these instead of implementing inline.
One source of truth per behavior.
"""
from rest_framework import serializers

from apps.orgs.models import OrgBase


def validate_customer_id(value):
    """Validate customer_id for any transaction header.

    Rejects non-positive values. Verifies OrgBase existence.
    Used by: ProposalSerializer, OrderSerializer, InvoiceSerializer,
    PurchaseSerializer, WorkOrderSerializer.
    """
    if value is not None and value <= 0:
        return None
    if value and value > 0:
        try:
            OrgBase.objects.get(id=value)
        except OrgBase.DoesNotExist:
            raise serializers.ValidationError("Customer organization does not exist.")
    return value


def validate_vendor_id(value):
    """Validate vendor_id for any transaction header.

    Rejects non-positive values. Verifies OrgBase existence.
    """
    if value is not None and value <= 0:
        return None
    if value and value > 0:
        try:
            OrgBase.objects.get(id=value)
        except OrgBase.DoesNotExist:
            raise serializers.ValidationError("Vendor organization does not exist.")
    return value


def validate_customer_vendor_different(data):
    """Cross-field validation: customer and vendor must differ.

    Call from serializer's validate() method:
        def validate(self, data):
            validate_customer_vendor_different(data)
            return data
    """
    cid = data.get('customer_id')
    vid = data.get('vendor_id')
    if cid and vid and cid == vid:
        raise serializers.ValidationError(
            "Customer and vendor cannot be the same entity."
        )


def validate_status_transition(instance, new_status):
    """Validate status transition using the centralized service.

    Call from serializer's validate_status() method:
        def validate_status(self, value):
            if self.instance:
                validate_status_transition(self.instance, value)
            return value

    Uses validate_status.py service — never hardcode allowed statuses.
    """
    if not instance:
        return  # new record, any initial status is fine
    from apps.transactions.services.validate_status import validate_transition
    result = validate_transition(
        instance=instance,
        model_type=instance._meta.model_name,
        to_status=new_status,
    )
    if not result.can_proceed:
        reason = '; '.join(result.errors) if result.errors else 'Status transition not allowed'
        raise serializers.ValidationError(reason)


# Base fields that every transaction header serializer should expose
TRANSACTION_HEADER_FIELDS = [
    'id', 'uuid', 'ida', 'status', 'attention', 'priority',
    'dt_created', 'dt_modified', 'dt_needed',
    'customer_id', 'vendor_id', 'manufacturer_id',
    'ship_via', 'is_active',
    'totals', 'finance', 'shipping', 'commission',
    'metadata', 'refs', 'prefs', 'config', 'comments',
    'health_rating',
]

TRANSACTION_HEADER_READ_ONLY = [
    'id', 'uuid', 'dt_created', 'dt_modified', 'totals',
    'health_rating',
]
