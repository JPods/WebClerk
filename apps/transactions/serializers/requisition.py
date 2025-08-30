from common.base_serializers import RoleAwareModelSerializer
from apps.transactions.models.requisition import RequisitionStd

class RequisitionSerializer(RoleAwareModelSerializer):
    table_name = 'requisitions'

    class Meta:
        model = RequisitionStd
        fields = '__all__'
        read_only_fields = ['id','uuid','version','created_dt','modified_dt']
