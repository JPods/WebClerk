from rest_framework import generics, status
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiResponse
from ..serializers import EmailSerializer
from ..models import Email
from core.models import Contact
from rest_framework.permissions import IsAuthenticated
from django.db import models
from core.utils import get_accessible_fields

class EmailView(generics.ListCreateAPIView):
    """Handles listing and creating emails with role-based field access."""
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
        email = serializer.save()
        contact_id = request.data.get('contact_id')
        if contact_id:
            try:
                contact = Contact.objects.get(id=contact_id)
                contact.refs.setdefault('emails', []).append(str(email.id))
                contact.save()
            except Contact.DoesNotExist:
                email.delete()
                return Response({"contact_id": "Invalid contact ID"}, status=status.HTTP_400_BAD_REQUEST)
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