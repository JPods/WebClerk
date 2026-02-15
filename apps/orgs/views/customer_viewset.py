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


class OrgBaseViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only ViewSet for OrgBase. Writes go through /wcapi/save/."""

    queryset = OrgBase.objects.active()
    serializer_class = OrgBaseSerializer
    permission_classes = [IsAuthenticated]


class CustomerViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only ViewSet for Customer. Writes go through /wcapi/save/."""

    queryset = Customer.objects.filter(is_active=True, is_deleted=False)
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]


class VendorViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only ViewSet for Vendor. Writes go through /wcapi/save/."""

    queryset = Vendor.objects.filter(is_active=True, is_deleted=False)
    serializer_class = VendorSerializer
    permission_classes = [IsAuthenticated]


class RepViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only ViewSet for Rep. Writes go through /wcapi/save/."""

    queryset = Rep.objects.filter(is_active=True, is_deleted=False)
    serializer_class = RepSerializer
    permission_classes = [IsAuthenticated]


class EmployeeViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only ViewSet for Employee. Writes go through /wcapi/save/."""

    queryset = Employee.objects.filter(is_active=True, is_deleted=False)
    serializer_class = EmployeeSerializer
    permission_classes = [IsAuthenticated]


class ManufacturerViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only ViewSet for Manufacturer. Writes go through /wcapi/save/."""

    queryset = Manufacturer.objects.filter(is_active=True, is_deleted=False)
    serializer_class = ManufacturerSerializer
    permission_classes = [IsAuthenticated]
