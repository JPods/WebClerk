from rest_framework import serializers

from common.base_serializers import RoleAwareModelSerializer
from apps.transactions.models import Proposal, ProposalLine
from apps.orgs.models import OrgBase
from .helpers import _name_from_refs, BASE_RO
from .base_line_serializer import BaseLineSerializer


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

    def validate_status(self, value):
        valid_statuses = ['planned', 'sent', 'accepted', 'rejected', 'cancelled']
        if value not in valid_statuses:
            raise serializers.ValidationError(f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
        return value

    def validate_customer_id(self, value):
        if value and value > 0:
            try:
                OrgBase.objects.get(id=value)
            except OrgBase.DoesNotExist:
                raise serializers.ValidationError("Customer organization does not exist.")
        return value

    def validate_vendor_id(self, value):
        if value and value > 0:
            try:
                OrgBase.objects.get(id=value)
            except OrgBase.DoesNotExist:
                raise serializers.ValidationError("Vendor organization does not exist.")
        return value

    def validate(self, data):
        if data.get('customer_id') and data.get('vendor_id') and data['customer_id'] == data['vendor_id']:
            raise serializers.ValidationError("Customer and vendor cannot be the same entity.")
        return data
