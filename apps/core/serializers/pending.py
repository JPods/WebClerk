from rest_framework import serializers
from apps.core.models import Pending


class PendingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pending
        fields = ['id','uuid','ida','table_name','record_id','data','dt_processed','created_dt','modified_dt','version']
        read_only_fields = ['id','uuid','created_dt','modified_dt','version','dt_processed']
