from rest_framework import serializers
from apps.core.models.template import Template
from apps.core.utils import get_accessible_fields

class TemplateSerializer(serializers.ModelSerializer):
    """Serializer for Template model with role-based field filtering."""
    metadata = serializers.JSONField(required=False)
    refs = serializers.JSONField(required=False)
    prefs = serializers.JSONField(required=False)
    comments = serializers.JSONField(required=False)

    class Meta:
        model = Template
        fields = [
            'id','uuid','name','purpose','table_name','is_active',
            'metadata','refs','prefs','comments','version','dt_created','dt_modified'
        ]
    read_only_fields = ['id','uuid','version','dt_created','dt_modified']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and hasattr(request,'user') and request.user.is_authenticated:
            mode = 'edit' if request.method in ['POST','PUT','PATCH'] else 'view'
            allowed = set(get_accessible_fields('templates', mode, request.user))
            core_fields = {'id','uuid','version','dt_created','dt_modified','name','purpose','table_name'}
            if allowed:
                for fname in list(self.fields.keys()):
                    if fname not in allowed and fname not in core_fields:
                        self.fields.pop(fname, None)
