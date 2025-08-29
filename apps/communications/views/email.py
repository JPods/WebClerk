# filepath: /Users/williamjames/Documents/CommerceExpert/webClerk3/communications/views/email.py
from rest_framework import generics, status, pagination
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiResponse
from ..serializers import EmailSerializer
from ..models import Email
from apps.core.models import Contact
from rest_framework.permissions import IsAuthenticated
from django.db import models
from apps.core.utils import get_accessible_fields
from common.models import default_refs  # ✅ ADD THIS IMPORT

class CommPagination(pagination.PageNumberPagination):
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 500

class EmailView(generics.ListCreateAPIView):
    """Handles listing and creating emails with role-based field access."""
    queryset = Email.objects.all()
    serializer_class = EmailSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CommPagination

    def get_queryset(self):
        """Filter queryset based on user roles and viewable fields."""
        accessible_fields = get_accessible_fields('emails', 'view', self.request.user)
        if not accessible_fields:
            return Email.objects.none()
        return Email.objects.all()

    @extend_schema(
        summary="List Emails",
        description="Retrieve a list of emails, filtered by user role permissions from settings.",
        responses={
            200: EmailSerializer(many=True),
            401: OpenApiResponse(description="Unauthorized"),
            403: OpenApiResponse(description="Forbidden"),
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Create Email",
        description="Create a new email and link to a contact, restricted by role-based editable fields.",
        request=EmailSerializer,
        responses={
            201: EmailSerializer,
            400: OpenApiResponse(description="Invalid data"),
            401: OpenApiResponse(description="Unauthorized"),
            403: OpenApiResponse(description="Forbidden"),
        }
    )
    def post(self, request, *args, **kwargs):
        accessible_fields = get_accessible_fields('emails', 'edit', request.user)
        if not accessible_fields:
            return Response(
                {"detail": "No editable fields allowed for your role"},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

    
    
        # ✅ STEP 1: Create domain FIRST
        email = serializer.save()
        
        # ✅ STEP 2: Setup refs structure properly
        if not email.refs:
            email.refs = default_refs()

        if 'links' not in email.refs:
            email.refs['links'] = {}

        if 'contacts' not in email.refs['links']:
            email.refs['links']['contacts'] = []

        # ✅ STEP 3: Add contact ID to proper location
        if request.user.id not in email.refs['links']['contacts']:
            email.refs['links']['contacts'].append(request.user.id)
        
        # ✅ STEP 4: Save the updated refs
        email.save()
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class EmailDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Handles retrieving, updating, and deleting an email with role-based field access."""
    queryset = Email.objects.all()
    serializer_class = EmailSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter queryset based on user roles and viewable fields."""
        accessible_fields = get_accessible_fields('emails', 'view', self.request.user)
        if not accessible_fields:
            return Email.objects.none()
        return Email.objects.all()

    @extend_schema(
        summary="Get Email",
        description="Retrieve a specific email by ID, filtered by user role permissions from settings.",
        responses={
            200: EmailSerializer,
            401: OpenApiResponse(description="Unauthorized"),
            403: OpenApiResponse(description="Forbidden"),
            404: OpenApiResponse(description="Not found"),
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Update Email",
        description="Update an email (partial update), restricted by role-based editable fields.",
        request=EmailSerializer,
        responses={
            200: EmailSerializer,
            400: OpenApiResponse(description="Invalid data"),
            401: OpenApiResponse(description="Unauthorized"),
            403: OpenApiResponse(description="Forbidden"),
            404: OpenApiResponse(description="Not found"),
        }
    )
    def patch(self, request, *args, **kwargs):
        accessible_fields = get_accessible_fields('emails', 'edit', request.user)
        if not accessible_fields:
            return Response(
                {"detail": "No editable fields allowed for your role"},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().patch(request, *args, **kwargs)

    @extend_schema(
        summary="Delete Email",
        description="Delete an email and remove from contact refs, restricted by role-based permissions.",
        responses={
            204: OpenApiResponse(description="Successfully deleted"),
            401: OpenApiResponse(description="Unauthorized"),
            403: OpenApiResponse(description="Forbidden"),
            404: OpenApiResponse(description="Not found"),
        }
    )
    def delete(self, request, *args, **kwargs):
        accessible_fields = get_accessible_fields('emails', 'edit', request.user)
        if not accessible_fields:
            return Response(
                {"detail": "No editable fields allowed for your role"},
                status=status.HTTP_403_FORBIDDEN
            )

        email = self.get_object()
        Contact.objects.filter(refs__emails__contains=[str(email.id)]).update(
            **{'refs__emails': models.F('refs__emails').exclude(str(email.id))}
        )
        return super().delete(request, *args, **kwargs)