from common.base_serializers import RoleAwareModelSerializer
from apps.core.models.action import Action

class ActionSerializer(RoleAwareModelSerializer):
    table_name = 'actions'
    class Meta:
        model = Action
        fields = '__all__'
    read_only_fields = ['id','uuid','version','dt_created','dt_modified']
