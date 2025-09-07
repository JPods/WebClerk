from rest_framework import serializers
from apps.docs.models.document import Document


class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = [
            'id','uuid','name','slug','status','description','body','data','comment','confidential',
            'copyright','count_accessed','model_name','retention_period','security_level',
            'sequence','size_bytes','mime_type','path','checksum','is_active','dt_created',
            'dt_modified','version'
        ]
        read_only_fields = ['id','uuid','slug','dt_created','dt_modified','version','size_bytes','count_accessed']


class DocumentSearchSerializer(serializers.ModelSerializer):
    highlight_snippet = serializers.CharField(read_only=True)

    class Meta:
        model = Document
        fields = ['id','uuid','name','slug','status','description','security_level','highlight_snippet']


class DocumentReadmeListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = [
            'id','uuid','slug','name','description','security_level','dt_modified','count_accessed'
        ]
        read_only_fields = fields


class DocumentReadmeDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = [
            'id','uuid','slug','name','description','body','data','count_accessed','security_level',
            'dt_modified','version'
        ]
        read_only_fields = fields