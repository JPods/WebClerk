from rest_framework import serializers
from apps.transactions.services.validate_transaction import ValidationResult


class TransferValidationSerializer(serializers.Serializer):
    """Serializer for transfer validation requests."""

    source_type = serializers.ChoiceField(
        choices=['proposal', 'order', 'purchase', 'invoice', 'workorder'],
        help_text="Type of source transaction"
    )
    source_id = serializers.IntegerField(help_text="ID of source transaction")
    target_type = serializers.ChoiceField(
        choices=['proposal', 'order', 'invoice', 'payment', 'purchase', 'workorder'],
        help_text="Type of target transaction"
    )


class TransferValidationResponseSerializer(serializers.Serializer):
    """Serializer for transfer validation responses."""

    can_proceed = serializers.BooleanField()
    errors = serializers.ListField(child=serializers.CharField())
    warnings = serializers.ListField(child=serializers.CharField())
    data = serializers.DictField()


class TransferRequestSerializer(serializers.Serializer):
    """Serializer for transfer execution requests."""

    source_type = serializers.ChoiceField(
        choices=['proposal', 'order', 'purchase', 'invoice', 'workorder']
    )
    source_id = serializers.IntegerField()
    target_type = serializers.ChoiceField(
        choices=['proposal', 'order', 'invoice', 'payment', 'purchase', 'workorder']
    )
    line_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text="Specific line IDs to transfer (optional)"
    )
    transfer_all = serializers.BooleanField(
        default=True,
        help_text="Transfer all eligible lines"
    )
    preserve_source = serializers.BooleanField(
        default=True,
        help_text="Keep source transaction active"
    )
    target_status = serializers.CharField(
        required=False,
        help_text="Initial status for target transaction"
    )
    amount = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        required=False,
        help_text="Amount for payment applications"
    )


class TransferResponseSerializer(serializers.Serializer):
    """Serializer for transfer execution responses."""

    success = serializers.BooleanField()
    target_id = serializers.IntegerField(required=False)
    target_type = serializers.CharField(required=False)
    source_id = serializers.IntegerField()
    source_type = serializers.CharField(required=False)
    lines_transferred = serializers.IntegerField()
    line_mapping = serializers.DictField()
    source_preserved = serializers.BooleanField()
    target_status = serializers.CharField()
    errors = serializers.ListField(child=serializers.CharField(), required=False)


class PaymentApplicationRequestSerializer(serializers.Serializer):
    """Serializer for payment application requests."""

    payment_id = serializers.IntegerField()
    invoice_id = serializers.IntegerField()
    amount = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        required=False,
        help_text="Amount to apply (defaults to remaining payment amount)"
    )


class PaymentApplicationResponseSerializer(serializers.Serializer):
    """Serializer for payment application responses."""

    success = serializers.BooleanField()
    amount_applied = serializers.DecimalField(max_digits=15, decimal_places=2)
    invoice_balance_remaining = serializers.DecimalField(max_digits=15, decimal_places=2)
    payment_fully_applied = serializers.BooleanField()
    invoice_fully_paid = serializers.BooleanField()
    application_id = serializers.IntegerField()


class InventoryReservationRequestSerializer(serializers.Serializer):
    """Serializer for inventory reservation requests."""

    order_id = serializers.IntegerField(help_text="Sales order ID")


class InventoryReservationResponseSerializer(serializers.Serializer):
    """Serializer for inventory reservation responses."""

    reservations_created = serializers.IntegerField()
    lines_reserved = serializers.IntegerField()
    total_quantity_reserved = serializers.DecimalField(max_digits=15, decimal_places=2)


__all__ = [
    'TransferValidationSerializer',
    'TransferValidationResponseSerializer',
    'TransferRequestSerializer',
    'TransferResponseSerializer',
    'PaymentApplicationRequestSerializer',
    'PaymentApplicationResponseSerializer',
    'InventoryReservationRequestSerializer',
    'InventoryReservationResponseSerializer',
]
