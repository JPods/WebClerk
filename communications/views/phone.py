from rest_framework import generics, status
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiResponse
from ..serializers import PhoneSerializer
from ..models import Phone
from core.models import Contact
from rest_framework.permissions import IsAuthenticated
from django.db import models
from core.utils import get_accessible_fields

class PhoneView(generics.ListCreateAPIView):
    """Handles listing and creating phones with role-based field access."""
    queryset = Phone.objects.all()
    serializer_class = PhoneSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter queryset based on user roles and viewable fields."""
        accessible_fields = get_accessible_fields('phones', 'view', self.request.user)
        if not accessible_fields:
            return Phone.objects.none()
        return Phone.objects.all()

    @extend_schema(
        summary="List Phones",
        description="Retrieve a list of phones, filtered by user role permissions from settings.",
        responses={
            200: PhoneSerializer(many=True),
            401: OpenApiResponse(description="Unauthorized"),
            403: OpenApiResponse(description="Forbidden"),
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Create Phone",
        description="Create a new phone and link to a contact, restricted by role-based editable fields.",
        request=PhoneSerializer,
        responses={
            201: PhoneSerializer,
            400: OpenApiResponse(description="Invalid data"),
            401: OpenApiResponse(description="Unauthorized"),
            403: OpenApiResponse(description="Forbidden"),
        }
    )
    def post(self, request, *args, **kwargs):
        accessible_fields = get_accessible_fields('phones', 'edit', request.user)
        if not accessible_fields:
            return Response(
                {"detail": "No editable fields allowed for your role"},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone.refs.setdefault('contacts', []).append(request.user.id)
        phone = serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class PhoneDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Handles retrieving, updating, and deleting a phone with role-based field access."""
    queryset = Phone.objects.all()
    serializer_class = PhoneSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter queryset based on user roles and viewable fields."""
        accessible_fields = get_accessible_fields('phones', 'view', self.request.user)
        if not accessible_fields:
            return Phone.objects.none()
        return Phone.objects.all()

    @extend_schema(
        summary="Get Phone",
        description="Retrieve a specific phone by ID, filtered by user role permissions from settings.",
        responses={
            200: PhoneSerializer,
            401: OpenApiResponse(description="Unauthorized"),
            403: OpenApiResponse(description="Forbidden"),
            404: OpenApiResponse(description="Not found"),
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Update Phone",
        description="Update a phone (partial update), restricted by role-based editable fields.",
        request=PhoneSerializer,
        responses={
            200: PhoneSerializer,
            400: OpenApiResponse(description="Invalid data"),
            401: OpenApiResponse(description="Unauthorized"),
            403: OpenApiResponse(description="Forbidden"),
            404: OpenApiResponse(description="Not found"),
        }
    )
    def patch(self, request, *args, **kwargs):
        accessible_fields = get_accessible_fields('phones', 'edit', request.user)
        if not accessible_fields:
            return Response(
                {"detail": "No editable fields allowed for your role"},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().patch(request, *args, **kwargs)

    @extend_schema(
        summary="Delete Phone",
        description="Delete a phone and remove from contact refs, restricted by role-based permissions.",
        responses={
            204: OpenApiResponse(description="Successfully deleted"),
            401: OpenApiResponse(description="Unauthorized"),
            403: OpenApiResponse(description="Forbidden"),
            404: OpenApiResponse(description="Not found"),
        }
    )
    def delete(self, request, *args, **kwargs):
        accessible_fields = get_accessible_fields('phones', 'edit', request.user)
        if not accessible_fields:
            return Response(
                {"detail": "No editable fields allowed for your role"},
                status=status.HTTP_403_FORBIDDEN
            )

        phone = self.get_object()
        Contact.objects.filter(refs__phones__contains=[str(phone.id)]).update(
            **{'refs__phones': models.F('refs__phones').exclude(str(phone.id))}
        )
        return super().delete(request, *args, **kwargs)