from rest_framework import serializers
from .models import Contact

class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ['id', 'email', 'first_name', 'last_name', 'role']
        read_only_fields = ['id']

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = Contact
        fields = ['email', 'first_name', 'last_name', 'role', 'password']

    def create(self, validated_data):
        return Contact.objects.create_user(**validated_data)