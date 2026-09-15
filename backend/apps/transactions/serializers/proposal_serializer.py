from rest_framework import serializers

from common.base_serializers import RoleAwareModelSerializer
from apps.transactions.models import Proposal, ProposalLine
from .helpers import _name_from_refs, BASE_RO
from .base_line_serializer import BaseLineSerializer
from .behaviors import (
    validate_customer_id as _validate_customer_id,
    validate_vendor_id as _validate_vendor_id,
    validate_customer_vendor_different,
    validate_status_transition,
)


class ProposalLineRichSerializer(RoleAwareModelSerializer):
    """Rich serializer for nested display in ProposalSerializer."""

    class Meta:
        model = ProposalLine
        fields = [
            'id', 'uuid', 'ida', 'dt_created', 'dt_modified', 'version',
            'is_active', 'security_level', 'is_deleted', 'is_archived',
            'metadata', 'refs', 'prefs', 'actions', 'comments', 'health_rating',
            'price_level', 'status', 'item_fk', 'item',
            'quantity', 'cost', 'tax', 'physical', 'price', 'proposal',
        ]
        read_only_fields = BASE_RO


class ProposalLineSerializer(BaseLineSerializer):
    """CRUD serializer for ProposalLine with deep-merge and role filtering."""
    parent = serializers.PrimaryKeyRelatedField(queryset=Proposal.objects.all(), source='proposal')

    class Meta(BaseLineSerializer.Meta):
        model = ProposalLine
        fields = BaseLineSerializer.Meta.fields + ['parent']


class ProposalSerializer(RoleAwareModelSerializer):
    """Serializer for Proposal transactions.

    totals JSON envelope is the source of truth for all computed values
    (total, margin, margin_pc, balance, etc.). No flattening — React
    reads totals.total, totals.margin, totals.margin_pc directly.
    """

    line_count = serializers.IntegerField(read_only=True)
    customer_name = serializers.SerializerMethodField(read_only=True)
    vendor_name = serializers.SerializerMethodField(read_only=True)
    lines = ProposalLineRichSerializer(many=True, read_only=True)

    class Meta:
        model = Proposal
        fields = [
            'id', 'uuid', 'ida', 'status', 'customer_id', 'vendor_id',
            'customer_name', 'vendor_name',
            'cost', 'sell', 'totals',
            'finance', 'flow', 'source', 'refs', 'prefs', 'metadata',
            'line_count', 'lines',
            'dt_created', 'dt_modified', 'version'
        ]
        read_only_fields = [
            'id', 'uuid', 'dt_created', 'dt_modified', 'version', 'customer_name',
            'vendor_name', 'totals', 'line_count', 'lines'
        ]

    def get_customer_name(self, obj):
        return _name_from_refs(obj, 'customer')

    def get_vendor_name(self, obj):
        return _name_from_refs(obj, 'vendor')

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if hasattr(instance, 'lines'):
            try:
                data['line_count'] = instance.lines.count()
            except Exception:
                data['line_count'] = len(data.get('lines', []) or [])
        return data

    def validate_customer_id(self, value):
        return _validate_customer_id(value)

    def validate_vendor_id(self, value):
        return _validate_vendor_id(value)

    def validate_status(self, value):
        validate_status_transition(self.instance, value)
        return value

    def validate(self, data):
        validate_customer_vendor_different(data)
        return data
