from rest_framework import serializers
from apps.transactions.models import Payment, PaymentMethod, PaymentTerm, Invoice
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
    invoice_id = serializers.IntegerField(required=True)
    contact_id = serializers.IntegerField(required=True)
    payment_method_id = serializers.IntegerField(required=False, allow_null=True)
    payment_term_id = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = Payment
        fields = [
            "id", "invoice_id", "contact_id", "amount", "payment_date",
            "payment_method_id", "payment_term_id", "reference_number", "notes",
            "gateway", "gateway_transaction_id", "gateway_payment_intent_id", "status",
            "gateway_response", "processed_at", "reconciled", "reconciliation_date", "fee_amount",
            "dt_created", "dt_modified"
        ]
        read_only_fields = ["id", "dt_created", "dt_modified", "processed_at", "reconciliation_date"]

    def create(self, validated_data):
        invoice_id = validated_data.pop("invoice_id")
        contact_id = validated_data.pop("contact_id")
        payment_method_id = validated_data.pop("payment_method_id", None)
        payment_term_id = validated_data.pop("payment_term_id", None)

        try:
            invoice = Invoice.objects.get(pk=invoice_id)
        except Invoice.DoesNotExist:
            raise serializers.ValidationError({"invoice_id": "Invalid invoice id"})

        try:
            contact = Contact.objects.get(pk=contact_id)
        except Contact.DoesNotExist:
            raise serializers.ValidationError({"contact_id": "Invalid contact id"})

        validated_data["invoice_id"] = invoice
        validated_data["contact_id"] = contact

        if payment_method_id:
            try:
                payment_method = PaymentMethod.objects.get(pk=payment_method_id)
                validated_data["paymentmethod_id"] = payment_method
            except PaymentMethod.DoesNotExist:
                raise serializers.ValidationError({"payment_method_id": "Invalid payment method id"})

        if payment_term_id:
            try:
                payment_term = PaymentTerm.objects.get(pk=payment_term_id)
                validated_data["paymentterm_id"] = payment_term
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
                validated_data["invoice_id"] = invoice
            except Invoice.DoesNotExist:
                raise serializers.ValidationError({"invoice_id": "Invalid invoice id"})

        if contact_id:
            try:
                contact = Contact.objects.get(pk=contact_id)
                validated_data["contact_id"] = contact
            except Contact.DoesNotExist:
                raise serializers.ValidationError({"contact_id": "Invalid contact id"})

        if payment_method_id is not None:
            if payment_method_id:
                try:
                    payment_method = PaymentMethod.objects.get(pk=payment_method_id)
                    validated_data["paymentmethod_id"] = payment_method
                except PaymentMethod.DoesNotExist:
                    raise serializers.ValidationError({"payment_method_id": "Invalid payment method id"})
            else:
                validated_data["paymentmethod_id"] = None

        if payment_term_id is not None:
            if payment_term_id:
                try:
                    payment_term = PaymentTerm.objects.get(pk=payment_term_id)
                    validated_data["paymentterm_id"] = payment_term
                except PaymentTerm.DoesNotExist:
                    raise serializers.ValidationError({"payment_term_id": "Invalid payment term id"})
            else:
                validated_data["paymentterm_id"] = None

        return super().update(instance, validated_data)