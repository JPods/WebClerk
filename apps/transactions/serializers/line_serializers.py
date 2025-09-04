from rest_framework import serializers
from apps.core.permissions import get_role_field_rules
from apps.transactions.models.line_variants import (
    Proposal, ProposalLine,
    Order, OrderLine,
    Invoice, InvoiceLine,
    Purchase, PurchaseLine,
    Workorder, WorkorderLine,
    Requisition, RequisitionLine,
)
from apps.transactions.models.projects import Project
from .cost_validators import CostJSONField  # added


class BaseLineSerializer(serializers.ModelSerializer):
    cost = CostJSONField(required=False)

    class Meta:
        fields = [
            'id', 'parent_ref_id', 'status', 'type_sale', 'probability',
            'item', 'quantity', 'cost', 'price', 'tax', 'action', 'physical', 'flow', 'source',
            'created_dt', 'modified_dt'
        ]
        read_only_fields = ['id', 'parent_ref_id', 'created_dt', 'modified_dt']

    def _filter_representation(self, data: dict) -> dict:
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return data
        model = getattr(self.Meta, 'model', None)
        if model is None:
            return data
        rules = get_role_field_rules(model, getattr(request.user, 'role', ''))
        allowed = set(rules.get('view', [])) | {'id'}
        if 'created_dt' in data:
            allowed.add('created_dt')
        if 'modified_dt' in data:
            allowed.add('modified_dt')
        return {k: v for k, v in data.items() if k in allowed}

    def to_representation(self, instance):
        data = super().to_representation(instance)
        return self._filter_representation(data)

    def validate(self, attrs):
        request = self.context.get('request')
        if request and request.user.is_authenticated and request.method not in ('GET', 'HEAD', 'OPTIONS'):
            model = getattr(self.Meta, 'model', None)
            rules = get_role_field_rules(model, getattr(request.user, 'role', '')) if model else {"edit": []}
            editable = set(rules.get('edit', []))
            # reject disallowed field edits
            disallowed = [f for f in attrs.keys() if f not in editable]
            if disallowed:
                # Provide granular errors per field plus a summary key
                error_detail = {f: ["Not editable for role"] for f in disallowed}
                error_detail['detail'] = [f"Fields not editable for role: {', '.join(disallowed)}"]
                raise serializers.ValidationError(error_detail)
        return attrs


class ProposalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Proposal
        fields = ['id', 'name', 'created_dt']
        read_only_fields = ['id', 'created_dt']


class ProposalLineSerializer(BaseLineSerializer):
    parent = serializers.PrimaryKeyRelatedField(queryset=Proposal.objects.all())

    class Meta(BaseLineSerializer.Meta):
        model = ProposalLine
        fields = BaseLineSerializer.Meta.fields + ['parent']


class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['id', 'order_no', 'created_dt']
        read_only_fields = ['id', 'created_dt']


class OrderLineSerializer(BaseLineSerializer):
    parent = serializers.PrimaryKeyRelatedField(queryset=Order.objects.all())

    class Meta(BaseLineSerializer.Meta):
        model = OrderLine
        fields = BaseLineSerializer.Meta.fields + ['parent']


class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = ['id', 'invoice_no', 'created_dt']
        read_only_fields = ['id', 'created_dt']


class InvoiceLineSerializer(BaseLineSerializer):
    parent = serializers.PrimaryKeyRelatedField(queryset=Invoice.objects.all())

    class Meta(BaseLineSerializer.Meta):
        model = InvoiceLine
        fields = BaseLineSerializer.Meta.fields + ['parent']


class PurchaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Purchase
        fields = ['id', 'po_no', 'created_dt']
        read_only_fields = ['id', 'created_dt']


class PurchaseLineSerializer(BaseLineSerializer):
    parent = serializers.PrimaryKeyRelatedField(queryset=Purchase.objects.all())

    class Meta(BaseLineSerializer.Meta):
        model = PurchaseLine
        fields = BaseLineSerializer.Meta.fields + ['parent']


class WorkorderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workorder
        fields = ['id', 'work_no', 'created_dt']
        read_only_fields = ['id', 'created_dt']


class WorkorderLineSerializer(BaseLineSerializer):
    parent = serializers.PrimaryKeyRelatedField(queryset=Workorder.objects.all())

    class Meta(BaseLineSerializer.Meta):
        model = WorkorderLine
        fields = BaseLineSerializer.Meta.fields + ['parent']


class RequisitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Requisition
        fields = ['id', 'req_no', 'created_dt']
        read_only_fields = ['id', 'created_dt']


class RequisitionLineSerializer(BaseLineSerializer):
    parent = serializers.PrimaryKeyRelatedField(queryset=Requisition.objects.all())

    class Meta(BaseLineSerializer.Meta):
        model = RequisitionLine
        fields = BaseLineSerializer.Meta.fields + ['parent']


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = [
            'id', 'uuid', 'situation', 'objective', 'priority', 'status', 'attention',
            'contact_id', 'tasks', 'burndown', 'category', 'intent', 'logistics',
            'profit', 'profit_velocity', 'security_level', 'data', 'created_dt', 'modified_dt', 'version'
        ]
        read_only_fields = ['id', 'uuid', 'burndown', 'created_dt', 'modified_dt', 'version']

    def validate_priority(self, value):  # guard even though model clean enforces
        if not (1 <= value <= 5):
            raise serializers.ValidationError('Priority must be 1-5')
        return value

    def validate_burndown(self, value):
        if not (0 <= value <= 100):
            raise serializers.ValidationError('Burndown must be 0-100')
        return value

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Hide internal metrics if low role (reuse role rules infra later if desired)
        request = self.context.get('request')
        role = getattr(getattr(request, 'user', None), 'role', '') if request else ''
        if role not in ('admin', 'manager'):
            # remove profit velocity (example of conditional field hiding)
            data.pop('profit_velocity', None)
        return data
