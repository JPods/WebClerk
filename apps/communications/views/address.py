# filepath: /Users/williamjames/Documents/CommerceExpert/webClerk3/communications/views/address.py
from rest_framework import generics, status
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiResponse
from ..serializers import LocationSerializer
from ..models import Location
from apps.core.models import Contact
from rest_framework.permissions import IsAuthenticated
from django.db import models
from apps.core.utils import get_accessible_fields
from common.models import default_refs  # Add this import

class LocationView(generics.ListCreateAPIView):
    """Handles listing and creating addresses with role-based field access."""
    queryset = Location.objects.all()
    serializer_class = LocationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter queryset based on user roles and viewable fields."""
        accessible_fields = get_accessible_fields('addresses', 'view', self.request.user)
        if not accessible_fields:
            return Location.objects.none()
        return Location.objects.all()

    @extend_schema(
        summary="List Locationes",
        description="Retrieve a list of addresses, filtered by user role permissions from settings.",
        responses={
            200: LocationSerializer(many=True),
            401: OpenApiResponse(description="Unauthorized"),
            403: OpenApiResponse(description="Forbidden"),
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Create Location",
        description="Create a new address and link to a contact, restricted by role-based editable fields.",
        request=LocationSerializer,
        responses={
            201: LocationSerializer,
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
        
        # FIXED: Create address first, then set refs
        address = serializer.save()
        
        # FIXED: Properly handle refs.links.contacts structure
        if not address.refs:
            address.refs = default_refs()
        
        if 'links' not in address.refs:
            address.refs['links'] = {}
            
        if 'contacts' not in address.refs['links']:
            address.refs['links']['contacts'] = []
        
        # Add contact ID to the proper location
        if request.user.id not in address.refs['links']['contacts']:
            address.refs['links']['contacts'].append(request.user.id)
        
        # Save the updated refs
        address.save()
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)

# ... existing LocationView code ...

class LocationDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Handles retrieving, updating, and deleting an address with role-based field access."""
    queryset = Location.objects.all()
    serializer_class = LocationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter queryset based on user roles and viewable fields."""
        accessible_fields = get_accessible_fields('addresses', 'view', self.request.user)
        if not accessible_fields:
            return Location.objects.none()
        return Location.objects.all()

    @extend_schema(
        summary="Get Location",
        description="Retrieve a specific address by ID, filtered by user role permissions from settings.",
        responses={
            200: LocationSerializer,
            401: OpenApiResponse(description="Unauthorized"),
            403: OpenApiResponse(description="Forbidden"),
            404: OpenApiResponse(description="Not found"),
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Update Location",
        description="Update an address (partial update), restricted by role-based editable fields.",
        request=LocationSerializer,
        responses={
            200: LocationSerializer,
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
        summary="Delete Location",
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
        return super().delete(request, *args, **kwargs)