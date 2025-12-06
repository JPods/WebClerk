from rest_framework import serializers
from apps.orgs.models import Customer


class CustomerSerializer(serializers.ModelSerializer):
    """
    Serializer for Customer model with all relevant fields for API operations.
    """

    class Meta:
        model = Customer
        fields = [
            'id', 'display_name', 'status', 'is_active',
            'contacts', 'locations', 'phones', 'emails',
            'domains', 'relations', 'financial', 'data',
            'dt_created', 'dt_modified', 'version'
        ]
        read_only_fields = ['id', 'dt_created', 'dt_modified', 'version']

    def create(self, validated_data):
        """Ensure org_type is set to 'customer' on creation."""
        validated_data['org_type'] = 'customer'
        return super().create(validated_data)