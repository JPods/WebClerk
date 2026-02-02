from apps.orgs.models import Customer
from apps.orgs.serializers.orgbase_serializer import OrgBaseSerializer


class CustomerSerializer(OrgBaseSerializer):
    """Customer serializer (OrgBase proxy)."""

    class Meta(OrgBaseSerializer.Meta):
        model = Customer