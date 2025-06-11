from rest_framework import serializers
from ..models import Address

class AddressSerializer(serializers.ModelSerializer):
    """Serializer for Address model with role-based field filtering."""
    refs = serializers.JSONField(default=dict, help_text="References and links")
    prefs = serializers.JSONField(default=dict, help_text="Preferences")
    metadata = serializers.JSONField(default=dict, help_text="Metadata including health and history")

    class Meta:
        model = Address
        fields = [
            'id', 'uuid', 'address1', 'address2', 'address_type', 'city', 'country',
            'instructions', 'latitude', 'longitude', 'state', 'zip', 'full', 'comment',
            'refs', 'prefs', 'metadata'
        ]
        read_only_fields = ['id', 'uuid']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            user_roles = request.user.role if hasattr(request.user, 'role') else []
            allowed_fields = self.get_allowed_fields(user_roles)
            for field_name in set(self.fields) - set(allowed_fields):
                self.fields.pop(field_name, None)

    def get_allowed_fields(self, user_roles):
        """Define fields accessible based on user roles."""
        if 'SUPER' in user_roles:
            return self.Meta.fields
        elif 'ADMIN' in user_roles:
            return self.Meta.fields
        else:
            return ['id', 'address1', 'city', 'country', 'refs']