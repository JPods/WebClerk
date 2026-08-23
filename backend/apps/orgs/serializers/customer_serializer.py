from apps.orgs.models import Customer
from apps.orgs.serializers.orgbase_serializer import OrgBaseSerializer


class CustomerSerializer(OrgBaseSerializer):
    """Customer serializer — financial envelope intact (PJPV)."""
    class Meta(OrgBaseSerializer.Meta):
        model = Customer