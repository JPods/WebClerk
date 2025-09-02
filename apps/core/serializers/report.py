from rest_framework import serializers
from apps.core.models.report import Report  # type: ignore
from apps.core.utils import get_accessible_fields

class ReportSerializer(serializers.ModelSerializer):
    metadata = serializers.JSONField(required=False)
    refs = serializers.JSONField(required=False)
    prefs = serializers.JSONField(required=False)
    comments = serializers.JSONField(required=False)

    class Meta:
        model = Report
        fields = ['id','uuid','is_active','metadata','refs','prefs','comments','version','created_dt','modified_dt']
        read_only_fields = ['id','uuid','version','created_dt','modified_dt']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and hasattr(request,'user') and request.user.is_authenticated:
            mode = 'edit' if request.method in ['POST','PUT','PATCH'] else 'view'
            allowed = set(get_accessible_fields('reports', mode, request.user))
            for fname in list(self.fields.keys()):
                if fname not in allowed:
                    self.fields.pop(fname, None)
