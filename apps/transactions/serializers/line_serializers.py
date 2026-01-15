from rest_framework import serializers
from apps.core.permissions import get_role_field_rules
from apps.transactions.models import (
    Proposal, ProposalLine,
    SalesOrder, SalesOrderLine,
    Invoice, InvoiceLine,
    PurchaseOrder, PurchaseOrderLine,
    WorkOrder, WorkOrderLine,
    Requisition, RequisitionLine,
)
from apps.transactions.models.project import Project
from .cost_validators import CostJSONField  # added


class BaseLineSerializer(serializers.ModelSerializer):
    cost = CostJSONField(required=False)

    class Meta:
        fields = [
            'id', 'parent_id', 'status', 'type_sale', 'probability',
            'item', 'quantity', 'cost', 'price', 'tax', 'action', 'physical', 'flow', 'source',
            'dt_created', 'dt_modified'
        ]
    read_only_fields = ['id', 'parent_id', 'dt_created', 'dt_modified']

    def _filter_representation(self, data: dict) -> dict:
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return data
        model = getattr(self.Meta, 'model', None)
        if model is None:
            return data
        rules = get_role_field_rules(model, getattr(request.user, 'role', ''))
        allowed = set(rules.get('view', [])) | {'id'}
        if 'dt_created' in data:
            allowed.add('dt_created')
        if 'dt_modified' in data:
            allowed.add('dt_modified')
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
        
        # Prevent item_id changes on existing lines (security backstop)
        # R25 UI is primary defense; this catches malicious API calls
        if self.instance is not None:  # This is an UPDATE
            current_item = getattr(self.instance, 'item', {}) or {}
            current_item_id = current_item.get('item_id')
            
            new_item = attrs.get('item', {}) or {}
            new_item_id = new_item.get('item_id')
            
            # Only reject if new_item_id is provided AND differs from current
            if new_item_id is not None and current_item_id is not None:
                if new_item_id != current_item_id:
                    raise serializers.ValidationError({
                        'item': 'Item_id cannot be changed for any line. To change the item, please delete this line and add a new line with the correct item.'
                    })
        
        return attrs


class ProposalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Proposal
        fields = ['id', 'name', 'dt_created']
        read_only_fields = ['id', 'dt_created']


class ProposalLineSerializer(BaseLineSerializer):
    parent = serializers.PrimaryKeyRelatedField(queryset=Proposal.objects.all())

    class Meta(BaseLineSerializer.Meta):
        model = ProposalLine
        fields = BaseLineSerializer.Meta.fields + ['parent']


class SalesOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalesOrder
        fields = ['id', 'order_no', 'dt_created']
        read_only_fields = ['id', 'dt_created']


class SalesOrderLineSerializer(BaseLineSerializer):
    parent = serializers.PrimaryKeyRelatedField(queryset=SalesOrder.objects.all())

    class Meta(BaseLineSerializer.Meta):
        model = SalesOrderLine
        fields = BaseLineSerializer.Meta.fields + ['parent']


class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = ['id', 'ida', 'dt_created']
        read_only_fields = ['id', 'dt_created']


class InvoiceLineSerializer(BaseLineSerializer):
    parent = serializers.PrimaryKeyRelatedField(queryset=Invoice.objects.all())

    class Meta(BaseLineSerializer.Meta):
        model = InvoiceLine
        fields = BaseLineSerializer.Meta.fields + ['parent']


class PurchaseOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchaseOrder
        fields = ['id', 'po_no', 'dt_created']
        read_only_fields = ['id', 'dt_created']


class PurchaseOrderLineSerializer(BaseLineSerializer):
    parent = serializers.PrimaryKeyRelatedField(queryset=PurchaseOrder.objects.all())

    class Meta(BaseLineSerializer.Meta):
        model = PurchaseOrderLine
        fields = BaseLineSerializer.Meta.fields + ['parent']


class WorkOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkOrder
        fields = ['id', 'work_no', 'dt_created']
        read_only_fields = ['id', 'dt_created']


class WorkOrderLineSerializer(BaseLineSerializer):
    parent = serializers.PrimaryKeyRelatedField(queryset=WorkOrder.objects.all())

    class Meta(BaseLineSerializer.Meta):
        model = WorkOrderLine
        fields = BaseLineSerializer.Meta.fields + ['parent']


class RequisitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Requisition
        fields = ['id', 'req_no', 'dt_created']
        ref_name = 'TxRequisitionHeader'
        read_only_fields = ['id', 'dt_created']


class RequisitionLineSerializer(BaseLineSerializer):
    parent = serializers.PrimaryKeyRelatedField(queryset=Requisition.objects.all())

    class Meta(BaseLineSerializer.Meta):
        model = RequisitionLine
        fields = BaseLineSerializer.Meta.fields + ['parent']
        ref_name = 'TxRequisitionLine'


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = [
            'id', 'uuid', 'situation', 'objective', 'priority', 'status', 'attention',
            'contact_id', 'tasks', 'burndown', 'category', 'intent', 'logistics',
            'profit', 'profit_velocity', 'security_level', 'data', 'dt_created', 'dt_modified', 'version'
        ]
    read_only_fields = ['id', 'uuid', 'burndown', 'dt_created', 'dt_modified', 'version']

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
