from rest_framework import serializers
from apps.docs.models.document import Document


class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = [
            'id','uuid','name','status','description','body','data','comment','confidential',
            'copyright','count_accessed','table_name','retention_period','security_level',
            'sequence','size_bytes','mime_type','path','checksum','is_active','created_dt',
            'modified_dt','version'
        ]
        read_only_fields = ['id','uuid','created_dt','modified_dt','version','size_bytes','count_accessed']


class DocumentSearchSerializer(serializers.ModelSerializer):
    highlight_snippet = serializers.CharField(read_only=True)

    class Meta:
        model = Document
        fields = ['id','uuid','name','status','description','security_level','highlight_snippet']