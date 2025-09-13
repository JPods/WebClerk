from common.base_serializers import RoleAwareModelSerializer
from apps.transactions.models.requisition import RequisitionStd

class RequisitionSerializer(RoleAwareModelSerializer):
    model_name = 'requisition'

    class Meta:
        model = RequisitionStd
        fields = '__all__'
        ref_name = 'TxRequisitionStd'
    read_only_fields = ['id','uuid','version','dt_created','dt_modified']
