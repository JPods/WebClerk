from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from apps.core.models.contact import Contact


class ApiLoginSerializer(TokenObtainPairSerializer):
    """Login (email + password) -> JWT pair with email/role/name claims."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['email'] = user.email
        token['role'] = getattr(user, 'role', '')
        token['name_first'] = getattr(user, 'name_first', '')
        token['name_last'] = getattr(user, 'name_last', '')
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user
        data['email'] = getattr(user, 'email', '')
        data['role'] = getattr(user, 'role', '')
        data['name_first'] = getattr(user, 'name_first', '')
        data['name_last'] = getattr(user, 'name_last', '')
        return data


class ApiSignupSerializer(serializers.ModelSerializer):
    """Signup (email, password, name_first, name_last, role) -> Contact instance.

    View issues tokens so we only create and return user.
    """
    password = serializers.CharField(write_only=True, min_length=6)
    role = serializers.ChoiceField(choices=Contact.ROLE_CHOICES, required=False, default='user')

    class Meta:
        model = Contact
        fields = ['email', 'password', 'name_first', 'name_last', 'role']

    def validate_email(self, value):
        v = value.lower()
        if Contact.objects.filter(email=v).exists():
            raise serializers.ValidationError('Email already registered')
        return v

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = Contact(**validated_data)
        user.set_password(password)
        user.save()
        return user
