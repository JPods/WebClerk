from rest_framework import serializers
from apps.transactions.models import Payment, PaymentMethod, PaymentTerm, PaymentApplication, Invoice
from apps.core.models import Contact


class PaymentTermSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentTerm
        fields = ["id", "name", "description", "days", "is_active", "dt_created", "dt_modified"]
        read_only_fields = ["id", "dt_created", "dt_modified"]


class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = ["id", "name", "description", "is_active", "dt_created", "dt_modified"]
        read_only_fields = ["id", "dt_created", "dt_modified"]


class PaymentSerializer(serializers.ModelSerializer):
    """Serializer for Payment transactions.

    Full CRUD with FK resolution for invoice, contact, payment_method, payment_term.
    Gateway fields hidden from non-staff users.
    """
    invoice_id = serializers.IntegerField(required=False, allow_null=True)
    contact_id = serializers.IntegerField(required=True)
    payment_method_id = serializers.IntegerField(required=False, allow_null=True)
    payment_term_id = serializers.IntegerField(required=False, allow_null=True)
    refs = serializers.JSONField(required=False, allow_null=True)
    metadata = serializers.JSONField(required=False, allow_null=True)

    class Meta:
        model = Payment
        fields = [
            "id", "invoice_id", "contact_id", "amount", "available", "tendered", "change",
            "dt_payment",
            "payment_method_id", "payment_term_id", "reference_number", "notes",
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
        contact_id = validated_data.pop("contact_id")
        payment_method_id = validated_data.pop("payment_method_id", None)
        payment_term_id = validated_data.pop("payment_term_id", None)

        # invoice_id is optional (for order-level deposits)
        if invoice_id:
            try:
                invoice = Invoice.objects.get(pk=invoice_id)
                validated_data["invoice"] = invoice
            except Invoice.DoesNotExist:
                raise serializers.ValidationError({"invoice_id": "Invalid invoice id"})
        else:
            validated_data["invoice"] = None

        try:
            contact = Contact.objects.get(pk=contact_id)
        except Contact.DoesNotExist:
            raise serializers.ValidationError({"contact_id": "Invalid contact id"})

        validated_data["contact"] = contact

        if payment_method_id:
            try:
                payment_method = PaymentMethod.objects.get(pk=payment_method_id)
                validated_data["payment_method"] = payment_method
            except PaymentMethod.DoesNotExist:
                raise serializers.ValidationError({"payment_method_id": "Invalid payment method id"})

        if payment_term_id:
            try:
                payment_term = PaymentTerm.objects.get(pk=payment_term_id)
                validated_data["payment_term"] = payment_term
            except PaymentTerm.DoesNotExist:
                raise serializers.ValidationError({"payment_term_id": "Invalid payment term id"})

        return super().create(validated_data)

    def update(self, instance, validated_data):
        invoice_id = validated_data.pop("invoice_id", None)
        contact_id = validated_data.pop("contact_id", None)
        payment_method_id = validated_data.pop("payment_method_id", None)
        payment_term_id = validated_data.pop("payment_term_id", None)

        if invoice_id:
            try:
                invoice = Invoice.objects.get(pk=invoice_id)
                validated_data["invoice"] = invoice
            except Invoice.DoesNotExist:
                raise serializers.ValidationError({"invoice_id": "Invalid invoice id"})

        if contact_id:
            try:
                contact = Contact.objects.get(pk=contact_id)
                validated_data["contact"] = contact
            except Contact.DoesNotExist:
                raise serializers.ValidationError({"contact_id": "Invalid contact id"})

        if payment_method_id is not None:
            if payment_method_id:
                try:
                    payment_method = PaymentMethod.objects.get(pk=payment_method_id)
                    validated_data["payment_method"] = payment_method
                except PaymentMethod.DoesNotExist:
                    raise serializers.ValidationError({"payment_method_id": "Invalid payment method id"})
            else:
                validated_data["payment_method"] = None

        if payment_term_id is not None:
            if payment_term_id:
                try:
                    payment_term = PaymentTerm.objects.get(pk=payment_term_id)
                    validated_data["payment_term"] = payment_term
                except PaymentTerm.DoesNotExist:
                    raise serializers.ValidationError({"payment_term_id": "Invalid payment term id"})
            else:
                validated_data["payment_term"] = None

        return super().update(instance, validated_data)


class PaymentApplicationSerializer(serializers.ModelSerializer):
    """Serializer for Payment Application records."""

    class Meta:
        model = PaymentApplication
        fields = [
            'id', 'payment', 'invoice', 'amount', 'applied_at', 'notes',
            'dt_created', 'dt_modified', 'version'
        ]
        read_only_fields = ['id', 'dt_created', 'dt_modified', 'version']
