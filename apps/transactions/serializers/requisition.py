from common.base_serializers import RoleAwareModelSerializer
from apps.transactions.models import Requisition

class RequisitionSerializer(RoleAwareModelSerializer):
    model_name = 'requisition'

    class Meta:
        model = Requisition
        fields = '__all__'
        ref_name = 'TxRequisitionStd'
    read_only_fields = ['id','uuid','version','dt_created','dt_modified']
