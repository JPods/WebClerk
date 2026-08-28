"""Base line serializer with deep-merge, role filtering, and cost validation."""

from rest_framework import serializers
from apps.core.permissions import get_role_field_rules
from .cost_validators import CostJSONField


class BaseLineSerializer(serializers.ModelSerializer):
    cost = CostJSONField(required=False)

    # JSON fields that should deep-merge on PATCH/PUT (not replace)
    JSON_MERGE_FIELDS = {'item', 'quantity', 'cost', 'price', 'tax', 'physical'}

    class Meta:
        fields = [
            'id', 'status', 'price_level',
            'item', 'quantity', 'cost', 'price', 'tax', 'physical',
            'dt_created', 'dt_modified'
        ]
        read_only_fields = ['id', 'dt_created', 'dt_modified']

    def update(self, instance, validated_data):
        """Deep-merge JSON fields instead of replacing them entirely.

        When a PATCH request sends only a subset of keys for a JSON field
        (e.g., {"quantity": {"transferred": 5}}), we merge it with the existing
        value so other keys (like "staged") are preserved.
        """
        for field in self.JSON_MERGE_FIELDS:
            if field in validated_data and isinstance(validated_data[field], dict):
                existing = getattr(instance, field, None)
                if existing and isinstance(existing, dict):
                    # Deep merge: existing values as base, new values overlay
                    merged = {**existing, **validated_data[field]}
                    validated_data[field] = merged
        return super().update(instance, validated_data)

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
