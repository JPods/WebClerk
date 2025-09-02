# path: apps/communications/serializers/phone.py
from rest_framework import serializers
from ..models import Phone
from apps.core.utils import get_accessible_fields

class PhoneSerializer(serializers.ModelSerializer):
    """Serializer for Phone model with role-based field filtering.

    Removed legacy/non-existent fields: 'comment', 'dt_verified'. Added 'is_active',
    audit timestamps and version for consistency.
    """
    refs = serializers.JSONField(default=dict, help_text="References and links")
    prefs = serializers.JSONField(default=dict, help_text="Preferences")
    metadata = serializers.JSONField(default=dict, help_text="Metadata including health and history")

    class Meta:
        model = Phone
        fields = [
            'id', 'uuid', 'attention', 'country_code', 'format', 'name', 'number',
            'opt_out', 'is_active', 'created_dt', 'modified_dt', 'version',
            'refs', 'prefs', 'metadata'
        ]
        read_only_fields = ['id', 'uuid', 'is_active', 'created_dt', 'modified_dt', 'version']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            mode = 'edit' if request.method in ['POST', 'PATCH', 'PUT'] else 'view'
            allowed_fields = get_accessible_fields('phones', mode, request.user)
            for field_name in set(self.fields) - set(allowed_fields):
                self.fields.pop(field_name, None)