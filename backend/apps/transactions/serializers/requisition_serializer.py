from rest_framework import serializers

from common.base_serializers import RoleAwareModelSerializer
from apps.transactions.models import Requisition, RequisitionLine
from .helpers import BASE_RO
from .base_line_serializer import BaseLineSerializer


class RequisitionLineSerializer(BaseLineSerializer):
    """CRUD serializer for RequisitionLine with deep-merge and role filtering."""
    parent = serializers.PrimaryKeyRelatedField(queryset=Requisition.objects.all())

    class Meta(BaseLineSerializer.Meta):
        model = RequisitionLine
        fields = BaseLineSerializer.Meta.fields + ['parent']
        ref_name = 'TxRequisitionLine'


class RequisitionSerializer(RoleAwareModelSerializer):
    model_name = 'requisition'

    class Meta:
        model = Requisition
        fields = [
            'id', 'uuid', 'ida', 'dt_created', 'dt_modified', 'version',
            'is_active', 'security_level', 'is_deleted', 'is_archived',
            'metadata', 'refs', 'prefs', 'actions', 'comments', 'health_rating',
            'name', 'purpose', 'status',
        ]
        ref_name = 'TxRequisitionStd'
        read_only_fields = BASE_RO
