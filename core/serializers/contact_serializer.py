from rest_framework import serializers
from ..models import Contact
import uuid
from django.utils import timezone
from datetime import timedelta
from drf_spectacular.utils import extend_schema_field, OpenApiTypes

class ContactSerializer(serializers.ModelSerializer):
    """Serializer for Contact model, exposing user details."""
    role = serializers.ListField(
        child=serializers.ChoiceField(choices=Contact.ROLE_CHOICES),
        help_text="List of user roles (e.g., ['ADMIN', 'SALE'])"
    )
    opt_out = serializers.JSONField(default=dict, help_text="Optional opt-out preferences")
    prefs = serializers.JSONField(default=dict, help_text="User preferences")
    refs = serializers.JSONField(default=dict, help_text="References and links")
    metadata = serializers.JSONField(default=dict, help_text="Metadata including health and history")

    class Meta:
        model = Contact
        fields = [
            'id', 'uuid', 'email', 'opt_out', 'role', 'is_email_verified', 'is_active', 'is_staff',
            'last_login', 'attention', 'comment_alert', 'company', 'name_first', 'name_last', 'name_middle',
            'prefix', 'suffix', 'salutation', 'publish', 'rank', 'date_joined', 'comment',
            'verification_code', 'verification_code_expiry', 'refs', 'prefs', 'metadata'
        ]
        read_only_fields = ['id', 'uuid', 'verification_code', 'verification_code_expiry', 'is_email_verified', 'date_joined', 'last_login']

class RegisterSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""
    password = serializers.CharField(write_only=True, help_text="User password (minimum 8 characters)")
    role = serializers.MultipleChoiceField(
        choices=Contact.ROLE_CHOICES,
        required=False,
        allow_blank=True,
        help_text="List of roles to assign (e.g., ['ADMIN', 'SALE'])"
    )
    opt_out = serializers.JSONField(default=dict, help_text="Optional opt-out preferences")
    prefs = serializers.JSONField(default=dict, help_text="User preferences")
    refs = serializers.JSONField(default=dict, help_text="References and links")
    metadata = serializers.JSONField(default=dict, help_text="Metadata including health and history")

    class Meta:
        model = Contact
        fields = [
            'email', 'opt_out', 'role', 'password', 'is_staff', 'attention', 'comment_alert',
            'company', 'name_first', 'name_last', 'name_middle', 'prefix', 'suffix', 'salutation',
            'publish', 'rank', 'comment', 'refs', 'prefs', 'metadata'
        ]

    def to_internal_value(self, data):
        # Move undefined fields to metadata.undefined
        defined_fields = set(self.fields.keys())
        undefined_fields = {key: value for key, value in data.items() if key not in defined_fields}
        
        if undefined_fields:
            metadata = data.get('metadata', {}).copy()
            metadata.setdefault('undefined', {})
            metadata['undefined'].update(undefined_fields)
            data = data.copy()
            data['metadata'] = metadata
            for key in undefined_fields:
                data.pop(key, None)

        return super().to_internal_value(data)

    def create(self, validated_data):
        if 'role' in validated_data:
            validated_data['role'] = list(validated_data['role'])
        validated_data['verification_code'] = str(uuid.uuid4())[:8]
        validated_data['verification_code_expiry'] = timezone.now() + timedelta(hours=24)
        validated_data['is_active'] = True
        password = validated_data.pop('password')
        validated_data['email'] = validated_data['email'].lower()
        user = Contact(**validated_data)
        user.set_password(password)
        user.save()
        return user