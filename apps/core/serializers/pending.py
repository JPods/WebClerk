from rest_framework import serializers
from apps.core.models import Pending


class PendingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pending
        fields = ['id','uuid','ida','table_name','record_id','data','dt_processed','dt_created','dt_modified','version']
        read_only_fields = ['id','uuid','dt_created','dt_modified','version','dt_processed']
