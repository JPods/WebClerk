from common.base_serializers import RoleAwareModelSerializer
from apps.transactions.models import Requisition


_BASE_RO = [
    'id', 'uuid', 'dt_created', 'dt_modified', 'version',
    'is_deleted', 'is_archived', 'metadata', 'refs', 'prefs',
    'actions', 'comments', 'health_rating',
]


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
        read_only_fields = _BASE_RO
