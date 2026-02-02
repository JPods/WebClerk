from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.orgs.models import Customer, Employee, Manufacturer, OrgBase, Rep, Vendor
from apps.orgs.serializers import (
    CustomerSerializer,
    EmployeeSerializer,
    ManufacturerSerializer,
    OrgBaseSerializer,
    RepSerializer,
    VendorSerializer,
)


class OrgBaseViewSet(viewsets.ModelViewSet):
    """ViewSet for OrgBase model operations."""

    queryset = OrgBase.objects.all()
    serializer_class = OrgBaseSerializer
    permission_classes = [IsAuthenticated]


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


class VendorViewSet(viewsets.ModelViewSet):
    """ViewSet for Vendor model operations."""

    queryset = Vendor.objects.all()
    serializer_class = VendorSerializer
    permission_classes = [IsAuthenticated]


class RepViewSet(viewsets.ModelViewSet):
    """ViewSet for Rep model operations."""

    queryset = Rep.objects.all()
    serializer_class = RepSerializer
    permission_classes = [IsAuthenticated]


class EmployeeViewSet(viewsets.ModelViewSet):
    """ViewSet for Employee model operations."""

    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer
    permission_classes = [IsAuthenticated]


class ManufacturerViewSet(viewsets.ModelViewSet):
    """ViewSet for Manufacturer model operations."""

    queryset = Manufacturer.objects.all()
    serializer_class = ManufacturerSerializer
    permission_classes = [IsAuthenticated]
