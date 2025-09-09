from rest_framework import serializers
from apps.core.models.setting import Setting
from apps.core.constants.table_registry import VALID_MODEL_KEYS, TABLE_REGISTRY_BY_ENDPOINT
from apps.core.utils import get_accessible_fields

class SettingSerializer(serializers.ModelSerializer):
    """Serializer for Setting model with role-based allowed field filtering.

    Only exposes real model fields plus BaseModel envelopes. Allows dynamic
    field filtering using `get_accessible_fields('settings', mode, user)` to
    keep external contract consistent with other core serializers.
    """
    metadata = serializers.JSONField(required=False)
    refs = serializers.JSONField(required=False)
    prefs = serializers.JSONField(required=False)
    comments = serializers.JSONField(required=False)

    class Meta:
        model = Setting
        fields = [
            'id','uuid','name','purpose','role','model_name','is_active','data',
            'metadata','refs','prefs','comments','version','dt_created','dt_modified'
        ]
    read_only_fields = ['id','uuid','version','dt_created','dt_modified']

    # model_name-only; no table-name validation here

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and hasattr(request,'user') and request.user.is_authenticated:
            mode = 'edit' if request.method in ['POST','PUT','PATCH'] else 'view'
            allowed = set(get_accessible_fields('settings', mode, request.user))
            # Always keep identity + version fields
            core_fields = {'id','uuid','version','dt_created','dt_modified','name','purpose','model_name','data'}
            if allowed:
                for fname in list(self.fields.keys()):
                    if fname not in allowed and fname not in core_fields:
                        self.fields.pop(fname, None)

    def validate_model_name(self, value: str | None) -> str | None:
        if not value:
            return value
        target = value.strip().lower()
        if target in VALID_MODEL_KEYS:
            key = target
        elif target in TABLE_REGISTRY_BY_ENDPOINT:
            key = TABLE_REGISTRY_BY_ENDPOINT[target].key
        elif target + 's' in VALID_MODEL_KEYS:
            key = target + 's'
        else:
            raise serializers.ValidationError(f"Invalid model_name '{target}'. Must be one of: {', '.join(VALID_MODEL_KEYS)}")
        # return singular form
        return key[:-1] if key.endswith('s') else key
