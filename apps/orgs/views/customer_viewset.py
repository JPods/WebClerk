from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.orgs.models import Customer
from apps.orgs.serializers import CustomerSerializer


class CustomerViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Customer model operations.

    Provides CRUD operations for customers with proper authentication.
    """
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter queryset based on user permissions if needed."""
        return super().get_queryset()
