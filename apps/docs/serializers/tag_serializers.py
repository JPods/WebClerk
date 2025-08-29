from rest_framework import serializers
from apps.docs.models.tag import Tag

class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = [
            'id','uuid','name','purpose','status','security_level','comment','table_name','record_id',
            'data','count_accessed','sequence','is_active','created_dt','modified_dt','version'
        ]
        read_only_fields = ['id','uuid','created_dt','modified_dt','version','count_accessed']

class TagDetailSerializer(TagSerializer):
    children = serializers.SerializerMethodField()
    parent_id_value = serializers.SerializerMethodField()

    class Meta(TagSerializer.Meta):
        fields = TagSerializer.Meta.fields + ['children','parent_id_value']

    def get_children(self, obj: Tag):
        return obj.children_ids()

    def get_parent_id_value(self, obj: Tag):
        return obj.parent_id()
