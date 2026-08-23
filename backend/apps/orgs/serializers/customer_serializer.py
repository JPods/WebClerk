from apps.orgs.models import Customer
from apps.orgs.serializers.orgbase_serializer import OrgBaseSerializer
from apps.orgs.models.constants import flatten_financial_for_type
from rest_framework import serializers


class CustomerSerializer(OrgBaseSerializer):
    """Customer serializer (OrgBase proxy)."""

    financial = serializers.SerializerMethodField()

    def get_financial(self, obj):
        return flatten_financial_for_type(getattr(obj, "financial", None), "customer")

    class Meta(OrgBaseSerializer.Meta):
        model = Customer