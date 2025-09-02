from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from ..models import Contact
from common.models import default_metadata
import uuid
from django.utils import timezone
from datetime import timedelta
from apps.core.utils import get_accessible_fields

class LoginSerializer(TokenObtainPairSerializer):
    """Obtain JWT pair with basic role validation and enriched custom claims.

    NOTE: Model uses a single string field `role` (not a list). Earlier code used
    membership (role in user.role) which incorrectly treated the role string as
    an iterable of characters. We now enforce simple equality.
    """
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)
    role = serializers.ChoiceField(choices=Contact.ROLE_CHOICES, required=True, help_text="Single role value (e.g., 'admin')")

    @classmethod
    def get_token(cls, user):  # add custom claims into JWT access token
        token = super().get_token(user)
        token['role'] = user.role
        token['email'] = user.email
        # lightweight display name
        token['name'] = user.get_full_name() or user.email
        return token

    def validate(self, attrs):
        # Standard username/password validation (calls authenticate)
        data = super().validate(attrs)
        user = getattr(self, 'user', None)
        if user is None:
            raise serializers.ValidationError({"error": "Invalid credentials."})
        requested_role = attrs.get('role')
        if requested_role and requested_role != user.role:
            raise serializers.ValidationError({"error": f"Role '{requested_role}' mismatch for this user."})
        # Add mirrored custom claims into response body for client bootstrapping
        data['role'] = user.role
        data['email'] = user.email
        data['name'] = user.get_full_name() or user.email
        return data

class ContactSerializer(serializers.ModelSerializer):
    """Serializer for Contact model with role-based field filtering.

    Trimmed to only include fields that actually exist on Contact. Legacy / planned
    fields (role_default, attention, publish, rank, verification_code, etc.) were
    removed to avoid exposing non-existent attributes that caused drift and potential
    runtime KeyErrors.
    """
    role = serializers.ChoiceField(choices=Contact.ROLE_CHOICES)
    # JSON envelope fields supplied by BaseModel
    refs = serializers.JSONField(required=False)
    prefs = serializers.JSONField(required=False)
    metadata = serializers.JSONField(required=False)
    comments = serializers.JSONField(required=False)

    class Meta:
        model = Contact
        fields = [
            'id', 'uuid', 'email', 'role', 'is_active', 'is_staff', 'last_login',
            'company', 'title', 'department', 'name_first', 'name_last', 'name_middle',
            'name_prefix', 'name_suffix', 'comment', 'date_joined',
            'refs', 'prefs', 'metadata', 'comments'
        ]
        read_only_fields = ['id', 'uuid', 'date_joined', 'last_login']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            mode = 'edit' if request.method in ['POST', 'PATCH', 'PUT'] else 'view'
            allowed_fields = get_accessible_fields('contacts', mode, request.user)
            # Only keep intersection to avoid silently dropping required base fields unexpectedly
            for field_name in list(self.fields.keys()):
                if field_name not in allowed_fields:
                    self.fields.pop(field_name, None)

class RegisterSerializer(serializers.ModelSerializer):
    """Serializer for user registration (single role string)."""
    password = serializers.CharField(write_only=True, help_text="User password (minimum 8 characters)")
    role = serializers.ChoiceField(choices=Contact.ROLE_CHOICES, required=False, default='user')
    refs = serializers.JSONField(required=False)
    prefs = serializers.JSONField(required=False)
    metadata = serializers.JSONField(required=False)
    comments = serializers.JSONField(required=False)

    class Meta:
        model = Contact
        fields = [
            'email', 'password', 'role', 'company', 'title', 'department',
            'name_first', 'name_last', 'name_middle', 'name_prefix', 'name_suffix',
            'comment', 'refs', 'prefs', 'metadata', 'comments'
        ]

    def to_internal_value(self, data):
        # Capture undefined fields into metadata.undefined for forward compatibility
        defined_fields = set(self.fields.keys())
        incoming = data.copy()
        metadata = incoming.get('metadata', default_metadata()).copy()
        undefined = {k: v for k, v in incoming.items() if k not in defined_fields}
        if undefined:
            metadata.setdefault('undefined', {}).update(undefined)
            for k in undefined:
                incoming.pop(k, None)
            incoming['metadata'] = metadata
        return super().to_internal_value(incoming)

    def create(self, validated_data):
        password = validated_data.pop('password')
        validated_data['email'] = validated_data['email'].lower()
        user = Contact(**validated_data)
        user.set_password(password)
        user.save()
        return user

class VerifyEmailSerializer(serializers.Serializer):  # kept for compatibility; now a no-op placeholder
    email = serializers.EmailField(required=True)
    code = serializers.CharField(required=True, max_length=8)

    def validate(self, attrs):  # simplified: Contact no longer tracks verification codes
        # Always fail to make clients migrate off legacy verification flow, but in a controlled way.
        raise serializers.ValidationError({"error": "Email verification flow deprecated."})