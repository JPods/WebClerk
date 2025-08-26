# filepath: /Users/williamjames/Documents/CommerceExpert/webClerk3/communications/views/domain.py
from rest_framework import generics, status
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiResponse
from ..serializers import DomainSerializer
from ..models import Domain
from apps.core.models import Contact
from rest_framework.permissions import IsAuthenticated
from django.db import models
from apps.core.utils import get_accessible_fields
from common.models import default_refs  # ✅ ADD THIS IMPORT

class DomainView(generics.ListCreateAPIView):
    """Handles listing and creating domains with role-based field access."""
    queryset = Domain.objects.all()
    serializer_class = DomainSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter queryset based on user roles and viewable fields."""
        accessible_fields = get_accessible_fields('domains', 'view', self.request.user)
        if not accessible_fields:
            return Domain.objects.none()
        return Domain.objects.all()

    @extend_schema(
        summary="List Domains",
        description="Retrieve a list of domains, filtered by user role permissions from settings.",
        responses={
            200: DomainSerializer(many=True),
            401: OpenApiResponse(description="Unauthorized"),
            403: OpenApiResponse(description="Forbidden"),
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Create Domain",
        description="Create a new domain and link to a contact, restricted by role-based editable fields.",
        request=DomainSerializer,
        responses={
            201: DomainSerializer,
            400: OpenApiResponse(description="Invalid data"),
            401: OpenApiResponse(description="Unauthorized"),
            403: OpenApiResponse(description="Forbidden"),
        }
    )
    def post(self, request, *args, **kwargs):
        accessible_fields = get_accessible_fields('domains', 'edit', request.user)
        if not accessible_fields:
            return Response(
                {"detail": "No editable fields allowed for your role"},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # ✅ STEP 1: Create domain FIRST
        domain = serializer.save()
        
        # ✅ STEP 2: Setup refs structure properly
        if not domain.refs:
            domain.refs = default_refs()
        
        if 'links' not in domain.refs:
            domain.refs['links'] = {}
            
        if 'contacts' not in domain.refs['links']:
            domain.refs['links']['contacts'] = []
        
        # ✅ STEP 3: Add contact ID to proper location
        if request.user.id not in domain.refs['links']['contacts']:
            domain.refs['links']['contacts'].append(request.user.id)
        
        # ✅ STEP 4: Save the updated refs
        domain.save()
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class DomainDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Handles retrieving, updating, and deleting a domain with role-based field access."""
    queryset = Domain.objects.all()
    serializer_class = DomainSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter queryset based on user roles and viewable fields."""
        accessible_fields = get_accessible_fields('domains', 'view', self.request.user)
        if not accessible_fields:
            return Domain.objects.none()
        return Domain.objects.all()

    @extend_schema(
        summary="Get Domain",
        description="Retrieve a specific domain by ID, filtered by user role permissions from settings.",
        responses={
            200: DomainSerializer,
            401: OpenApiResponse(description="Unauthorized"),
            403: OpenApiResponse(description="Forbidden"),
            404: OpenApiResponse(description="Not found"),
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Update Domain",
        description="Update a domain (partial update), restricted by role-based editable fields.",
        request=DomainSerializer,
        responses={
            200: DomainSerializer,
            400: OpenApiResponse(description="Invalid data"),
            401: OpenApiResponse(description="Unauthorized"),
            403: OpenApiResponse(description="Forbidden"),
            404: OpenApiResponse(description="Not found"),
        }
    )
    def patch(self, request, *args, **kwargs):
        accessible_fields = get_accessible_fields('domains', 'edit', request.user)
        if not accessible_fields:
            return Response(
                {"detail": "No editable fields allowed for your role"},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().patch(request, *args, **kwargs)

    @extend_schema(
        summary="Delete Domain",
        description="Delete a domain and remove from contact refs, restricted by role-based permissions.",
        responses={
            204: OpenApiResponse(description="Successfully deleted"),
            401: OpenApiResponse(description="Unauthorized"),
            403: OpenApiResponse(description="Forbidden"),
            404: OpenApiResponse(description="Not found"),
        }
    )
    def delete(self, request, *args, **kwargs):
        accessible_fields = get_accessible_fields('domains', 'edit', request.user)
        if not accessible_fields:
            return Response(
                {"detail": "No editable fields allowed for your role"},
                status=status.HTTP_403_FORBIDDEN
            )

        domain = self.get_object()
        Contact.objects.filter(refs__domains__contains=[str(domain.id)]).update(
            **{'refs__domains': models.F('refs__domains').exclude(str(domain.id))}
        )
        return super().delete(request, *args, **kwargs)