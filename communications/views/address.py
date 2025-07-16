from rest_framework import generics, status
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiResponse
from ..serializers import AddressSerializer
from ..models import Address
from core.models import Contact
from rest_framework.permissions import IsAuthenticated
from django.db import models
from core.utils import get_accessible_fields

class AddressView(generics.ListCreateAPIView):
    """Handles listing and creating addresses with role-based field access."""
    queryset = Address.objects.all()
    serializer_class = AddressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter queryset based on user roles and viewable fields."""
        accessible_fields = get_accessible_fields('addresses', 'view', self.request.user)
        if not accessible_fields:
            return Address.objects.none()
        return Address.objects.all()

    @extend_schema(
        summary="List Addresses",
        description="Retrieve a list of addresses, filtered by user role permissions from settings.",
        responses={
            200: AddressSerializer(many=True),
            401: OpenApiResponse(description="Unauthorized"),
            403: OpenApiResponse(description="Forbidden"),
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Create Address",
        description="Create a new address and link to a contact, restricted by role-based editable fields.",
        request=AddressSerializer,
        responses={
            201: AddressSerializer,
            400: OpenApiResponse(description="Invalid data"),
            401: OpenApiResponse(description="Unauthorized"),
            403: OpenApiResponse(description="Forbidden"),
        }
    )
    def post(self, request, *args, **kwargs):
        accessible_fields = get_accessible_fields('addresses', 'edit', request.user)
        if not accessible_fields:
            return Response(
                {"detail": "No editable fields allowed for your role"},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        address = serializer.save()
        # Link to contact if provided
        try:
            contact_email = request.user.email.lower()
            if contact_email:
                contact = Contact.objects.get(email=contact_email)
                contact.refs.setdefault('addresses', []).append(str(address.id))
                contact.save()
        except Contact.DoesNotExist:
            address.delete()
            return Response({"contact": "Invalid contact email"}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class AddressDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Handles retrieving, updating, and deleting an address with role-based field access."""
    queryset = Address.objects.all()
    serializer_class = AddressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter queryset based on user roles and viewable fields."""
        accessible_fields = get_accessible_fields('addresses', 'view', self.request.user)
        if not accessible_fields:
            return Address.objects.none()
        return Address.objects.all()

    @extend_schema(
        summary="Get Address",
        description="Retrieve a specific address by ID, filtered by user role permissions from settings.",
        responses={
            200: AddressSerializer,
            401: OpenApiResponse(description="Unauthorized"),
            403: OpenApiResponse(description="Forbidden"),
            404: OpenApiResponse(description="Not found"),
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Update Address",
        description="Update an address (partial update), restricted by role-based editable fields.",
        request=AddressSerializer,
        responses={
            200: AddressSerializer,
            400: OpenApiResponse(description="Invalid data"),
            401: OpenApiResponse(description="Unauthorized"),
            403: OpenApiResponse(description="Forbidden"),
            404: OpenApiResponse(description="Not found"),
        }
    )
    def patch(self, request, *args, **kwargs):
        accessible_fields = get_accessible_fields('addresses', 'edit', request.user)
        if not accessible_fields:
            return Response(
                {"detail": "No editable fields allowed for your role"},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().patch(request, *args, **kwargs)

    @extend_schema(
        summary="Delete Address",
        description="Delete an address and remove from contact refs, restricted by role-based permissions.",
        responses={
            204: OpenApiResponse(description="Successfully deleted"),
            401: OpenApiResponse(description="Unauthorized"),
            403: OpenApiResponse(description="Forbidden"),
            404: OpenApiResponse(description="Not found"),
        }
    )
    def delete(self, request, *args, **kwargs):
        accessible_fields = get_accessible_fields('addresses', 'edit', request.user)
        if not accessible_fields:
            return Response(
                {"detail": "No editable fields allowed for your role"},
                status=status.HTTP_403_FORBIDDEN
            )

        address = self.get_object()
        # Remove from contact refs
        Contact.objects.filter(refs__addresses__contains=[str(address.id)]).update(
            **{'refs__addresses': models.F('refs__addresses').exclude(str(address.id))}
        )
        return super().delete(request, *args, **kwargs)