from rest_framework import serializers
from apps.transactions.models import Cash, Invoice
from apps.core.models import Contact


class CashSerializer(serializers.ModelSerializer):
    """Serializer for Cash (formerly Cash) transactions.

    Full CRUD with FK resolution for invoice and contact. terms is a Term ida (text),
    checked where every record's terms is checked — the save.
    Gateway fields hidden from non-staff users.
    """
    invoice_id = serializers.IntegerField(required=False, allow_null=True)
    contact_id = serializers.IntegerField(required=True)
    refs = serializers.JSONField(required=False, allow_null=True)
    metadata = serializers.JSONField(required=False, allow_null=True)

    class Meta:
        model = Cash
        fields = [
            "id", "invoice_id", "contact_id", "amount", "available", "tendered", "change",
            "dt_cash",
            "method", "terms", "reference_number",
            "gateway", "gateway_transaction_id", "gateway_payment_intent_id", "status",
            "gateway_response", "dt_processed", "reconciled", "dt_reconciliation", "fee_amount",
            "refs", "metadata",
            "dt_created", "dt_modified", "version"
        ]
        read_only_fields = ["id", "dt_created", "dt_modified", "dt_processed", "dt_reconciliation", "version",
                            "available", "change"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        if request and not getattr(request.user, 'is_staff', False):
            data.pop('gateway_response', None)
            data.pop('gateway_transaction_id', None)
            data.pop('gateway_payment_intent_id', None)
        return data

    def create(self, validated_data):
        invoice_id = validated_data.pop("invoice_id", None)
        contact_id = validated_data.pop("contact_id", None)

        # invoice_id is optional (for order-level deposits)
        if invoice_id:
            try:
                invoice = Invoice.objects.get(pk=invoice_id)
                validated_data["invoice"] = invoice
            except Invoice.DoesNotExist:
                raise serializers.ValidationError({"invoice_id": "Invalid invoice id"})
        else:
            validated_data["invoice"] = None

        # contact_id is a plain BigIntegerField — validate existence
        if contact_id:
            if not Contact.objects.filter(pk=contact_id).exists():
                raise serializers.ValidationError({"contact_id": "Invalid contact id"})
            validated_data["contact_id"] = contact_id

        return super().create(validated_data)

    def update(self, instance, validated_data):
        invoice_id = validated_data.pop("invoice_id", None)
        contact_id = validated_data.pop("contact_id", None)

        if invoice_id:
            try:
                invoice = Invoice.objects.get(pk=invoice_id)
                validated_data["invoice"] = invoice
            except Invoice.DoesNotExist:
                raise serializers.ValidationError({"invoice_id": "Invalid invoice id"})

        if contact_id:
            if not Contact.objects.filter(pk=contact_id).exists():
                raise serializers.ValidationError({"contact_id": "Invalid contact id"})
            validated_data["contact_id"] = contact_id

        return super().update(instance, validated_data)


