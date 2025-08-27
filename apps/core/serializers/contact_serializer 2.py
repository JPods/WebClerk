# filepath: /Users/williamjames/Documents/CommerceExpert/webClerk3/core/serializers/contact_serializer.py
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from ..models import Contact
<<<<<<< HEAD:core/serializers/contact_serializer.py
from common.models import default_metadata
from communications.models import Location, Email, Phone, Domain
=======
from common.base_model import default_metadata
from apps.communications.models import Location, Email, Phone, Domain
>>>>>>> 01558f6ebce5d18d828e022158343627fc8162d8:apps/core/serializers/contact_serializer.py
import uuid
from django.utils import timezone
from datetime import timedelta
from apps.core.utils import get_accessible_fields

class LoginSerializer(TokenObtainPairSerializer):
    """Serializer for user login, validating email, password, and role."""
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)
    role = serializers.ChoiceField(choices=Contact.ROLE_CHOICES, required=True, help_text="Single role value (e.g., 'USER')")

    def validate(self, attrs):
        email = attrs.get('email').lower()
        role = attrs.get('role')

        # Validate credentials
        data = super().validate(attrs)

        # Check if user exists and role is in their role array
        try:
            user = Contact.objects.get(email=email)
        except Contact.DoesNotExist:
            raise serializers.ValidationError({"error": "User with this email does not exist."})

        if role not in user.role:
            raise serializers.ValidationError({"error": f"Role '{role}' is not assigned to this user."})

        return data

class ContactSerializer(serializers.ModelSerializer):
    """Serializer for Contact model with role-based field filtering."""
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
            'id', 'uuid', 'email', 'opt_out', 'role', 'role_default', 'is_email_verified', 'is_active', 'is_staff',
            'last_login', 'attention', 'comment_alert', 'company', 'name_first', 'name_last', 'name_middle',
            'prefix', 'suffix', 'salutation', 'publish', 'rank', 'date_joined', 'comment',
            'verification_code', 'verification_code_expiry', 'refs', 'prefs', 'metadata'
        ]
        read_only_fields = ['id', 'uuid', 'verification_code', 'verification_code_expiry', 'is_email_verified', 'date_joined', 'last_login']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            mode = 'edit' if request.method in ['POST', 'PATCH', 'PUT'] else 'view'
            allowed_fields = get_accessible_fields('contacts', mode, request.user)
            for field_name in set(self.fields) - set(allowed_fields):
                self.fields.pop(field_name, None)

class RegisterSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""
    password = serializers.CharField(write_only=True, help_text="User password (minimum 8 characters)")
    role = serializers.MultipleChoiceField(
        choices=Contact.ROLE_CHOICES,
        required=False,
        allow_blank=True,
        default=['USER'],
        help_text="List of roles to assign (e.g., ['ADMIN', 'SALE'])"
    )
    opt_out = serializers.JSONField(default=dict, help_text="Optional opt-out preferences")
    prefs = serializers.JSONField(default=dict, help_text="User preferences")
    refs = serializers.JSONField(default=dict, help_text="References and links")
    metadata = serializers.JSONField(default=dict, help_text="Metadata including health and history")

    class Meta:
        model = Contact
        fields = [
            'email', 'opt_out', 'role', 'role_default', 'password', 'is_staff', 'attention', 'comment_alert',
            'company', 'name_first', 'name_last', 'name_middle', 'prefix', 'suffix', 'salutation',
            'publish', 'rank', 'comment', 'refs', 'prefs', 'metadata'
        ]

    def to_internal_value(self, data):
        # Move undefined fields to metadata.undefined
        defined_fields = set(self.fields.keys())
        undefined_fields = {key: value for key, value in data.items() if key not in defined_fields}
        
        data = data.copy()
        metadata = data.get('metadata', default_metadata()).copy()
        if undefined_fields:
            metadata['undefined'].update(undefined_fields)
            for key in undefined_fields:
                data.pop(key, None)
            data['metadata'] = metadata

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
<<<<<<< HEAD:core/serializers/contact_serializer.py
=======
        # Create blank objects
        location = Location.objects.create()
        email = Email.objects.create()
        phone = Phone.objects.create()
        domain = Domain.objects.create()
        user.refs.update({
            'locations': [str(location.id)],
            'emails': [str(email.id)],
            'phones': [str(phone.id)],
            'domains': [str(domain.id)]
        })
>>>>>>> 01558f6ebce5d18d828e022158343627fc8162d8:apps/core/serializers/contact_serializer.py
        user.save()
        return user

class VerifyEmailSerializer(serializers.Serializer):
    """Serializer for email verification."""
    email = serializers.EmailField(required=True)
    code = serializers.CharField(required=True, max_length=8)

    def validate(self, attrs):
        email = attrs.get('email').lower()
        code = attrs.get('code')
        try:
            user = Contact.objects.get(email=email)
        except Contact.DoesNotExist:
            raise serializers.ValidationError({"error": "User with this email does not exist."})
        
        if user.is_email_verified:
            raise serializers.ValidationError({"error": "Email is already verified."})
        
        if user.verification_code != code:
            raise serializers.ValidationError({"error": "Invalid verification code."})
        
        if user.verification_code_expiry < timezone.now():
            raise serializers.ValidationError({"error": "Verification code has expired."})
        
        return attrs