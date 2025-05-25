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

    class Meta:
        model = Contact
        fields = [
            'id', 'uuid', 'email', 'name_first', 'name_last', 'name_middle',
            'role', 'is_email_verified', 'verification_code',
            'verification_code_expiry', 'attention', 'comment_alert',
            'company', 'opt_out', 'prefix', 'publish', 'rank',
            'salutation', 'suffix', 'comment', 'refs', 'metadata'
        ]
        read_only_fields = ['id', 'uuid', 'verification_code', 'verification_code_expiry', 'is_email_verified']

class RegisterSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""
    password = serializers.CharField(write_only=True, help_text="User password (minimum 8 characters)")
    role = serializers.MultipleChoiceField(
        choices=Contact.ROLE_CHOICES,
        required=False,
        allow_blank=True,
        help_text="List of roles to assign (e.g., ['ADMIN', 'SALE'])"
    )

    class Meta:
        model = Contact
        fields = [
            'email', 'name_first', 'name_last', 'name_middle', 'role',
            'password', 'attention', 'comment_alert', 'company', 'opt_out',
            'prefix', 'publish', 'rank', 'salutation', 'suffix', 'comment',
            'refs', 'metadata'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.undefined_fields = {}

    def to_internal_value(self, data):
        defined_fields = set(self.fields.keys())
        self.undefined_fields = {key: value for key, value in data.items() if key not in defined_fields}
        return super().to_internal_value(data)

    def create(self, validated_data):
        if self.undefined_fields:
            metadata = validated_data.get('metadata', {})
            undefined = metadata.get('undefined', {})
            undefined.update(self.undefined_fields)
            metadata['undefined'] = undefined
            validated_data['metadata'] = metadata
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