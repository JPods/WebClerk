from __future__ import annotations

from rest_framework import serializers
from apps.products.models.bill_of_material import BillOfMaterial
from apps.products.models.item import Item


class BillOfMaterialSerializer(serializers.ModelSerializer):
    parent_id = serializers.PrimaryKeyRelatedField(queryset=Item.objects.all(), source="parent", write_only=True, required=True)
    component_id = serializers.PrimaryKeyRelatedField(queryset=Item.objects.all(), source="component", write_only=True, required=True)
    parent = serializers.PrimaryKeyRelatedField(read_only=True)
    component = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = BillOfMaterial
        fields = [
            'id', 'parent', 'parent_id', 'component', 'component_id', 'revision', 'effective_from', 'effective_to',
            'quantity', 'scrap_factor', 'yield_pct', 'sequence', 'is_alternate', 'alternate_group', 'is_optional',
            'cost_snapshot', 'op_data', 'change_reason', 'dt_last_recalc', 'dt_created', 'dt_modified', 'is_active'
        ]
        read_only_fields = ['cost_snapshot', 'dt_last_recalc', 'dt_created', 'dt_modified']

    def validate(self, attrs):  # additional cross-field logic beyond model.clean
        eff_from = attrs.get('effective_from')
        eff_to = attrs.get('effective_to')
        if eff_from and eff_to and eff_to < eff_from:
            raise serializers.ValidationError({"effective_to": "Must be >= effective_from"})
        return super().validate(attrs)
