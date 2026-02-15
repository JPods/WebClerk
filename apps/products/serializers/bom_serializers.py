from __future__ import annotations

from rest_framework import serializers
from apps.products.models.bill_of_material import BillOfMaterial
from apps.products.models.item import Item


class BOMComponentSerializer(serializers.ModelSerializer):
    """Nested serializer for component item details in BOM responses."""
    class Meta:
        model = Item
        fields = ['id', 'sku', 'name', 'description', 'uom']


class BOMChildSerializer(serializers.ModelSerializer):
    """Lightweight serializer for nested BOM children (one level deep)."""
    component = BOMComponentSerializer(source='child_item', read_only=True)
    extended_cost = serializers.SerializerMethodField()

    class Meta:
        model = BillOfMaterial
        fields = [
            'id', 'component', 'description', 'quantity', 'cost_snapshot', 
            'extended_cost', 'sequence', 'is_alternate', 'is_optional'
        ]

    def get_extended_cost(self, obj) -> float | None:
        if obj.cost_snapshot is not None and obj.quantity is not None:
            return float(obj.quantity * obj.cost_snapshot)
        return None


class BillOfMaterialSerializer(serializers.ModelSerializer):
    # Write fields - accept IDs
    parent_id = serializers.PrimaryKeyRelatedField(
        queryset=Item.objects.all(), source="parent_item", write_only=True, required=False
    )
    component_id_write = serializers.PrimaryKeyRelatedField(
        queryset=Item.objects.all(), source="child_item", write_only=True, required=False
    )
    
    # Read fields - return nested details
    parent_item = BOMComponentSerializer(source='parent_item', read_only=True)
    component = BOMComponentSerializer(source='child_item', read_only=True)
    
    # Computed fields
    extended_cost = serializers.SerializerMethodField()
    component_child_count = serializers.SerializerMethodField()
    refs = serializers.SerializerMethodField()

    class Meta:
        model = BillOfMaterial
        fields = [
            'id', 
            # Read - nested item details
            'parent_item', 'component',
            # Write - IDs
            'parent_id', 'component_id_write',
            # BOM fields
            'description', 'revision', 'dt_effective_from', 'dt_effective_to',
            'quantity', 'scrap_factor', 'yield_pct', 'sequence', 
            'is_alternate', 'alternate_group', 'is_optional',
            'cost_snapshot', 'extended_cost', 'component_child_count', 'refs',
            'op_data', 'change_reason', 
            'dt_last_recalc', 'dt_created', 'dt_modified', 'is_active'
        ]
        read_only_fields = ['dt_last_recalc', 'dt_created', 'dt_modified']

    def get_extended_cost(self, obj) -> float | None:
        """Calculate qty * cost_snapshot for display."""
        if obj.cost_snapshot is not None and obj.quantity is not None:
            return float(obj.quantity * obj.cost_snapshot)
        return None

    def get_component_child_count(self, obj) -> int:
        """Return count of BOM children for this component (0 if not a subassembly)."""
        if obj.child_item_id:
            return BillOfMaterial.objects.filter(parent_item_id=obj.child_item_id).count()
        return 0

    def get_refs(self, obj) -> dict:
        """Return nested references including BOM children of this component."""
        refs: dict = {'links': {'bom': []}}
        if obj.child_item_id:
            children = BillOfMaterial.objects.filter(
                parent_item_id=obj.child_item_id
            ).select_related('child_item').order_by('sequence', 'id')
            if children.exists():
                refs['links']['bom'] = BOMChildSerializer(children, many=True).data
        return refs

    def validate(self, attrs):
        eff_from = attrs.get('dt_effective_from')
        eff_to = attrs.get('dt_effective_to')
        if eff_from and eff_to and eff_to < eff_from:
            raise serializers.ValidationError({"dt_effective_to": "Must be >= dt_effective_from"})
        return super().validate(attrs)
