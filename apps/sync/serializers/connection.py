from rest_framework import serializers
from apps.sync.models.connection import Connection
from common.base_serializers import RoleAwareModelSerializer


class ConnectionSerializer(RoleAwareModelSerializer):
    class Meta:
        model = Connection
        fields = [
            'id','uuid','name','type','config','is_active','status','scripts','relationships','action','comment','purpose',
            'maps','encryption','rules','conflicts','changes','refs','prefs','metadata','dt_created','dt_modified','version'
        ]
    read_only_fields = ['id','uuid','dt_created','dt_modified','version']

    # model_name-only world; no table_name attribute