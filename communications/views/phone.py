from rest_framework import generics, status
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiResponse
from ..serializers import PhoneSerializer
from ..models import Phone
from core.models import Contact
from core.permissions import IsAuthenticatedActive, IsAdminOrSuper

class PhoneView(generics.ListCreateAPIView):
    """Handles listing and creating phones."""
    queryset = Phone.objects.all()
    serializer_class = PhoneSerializer
    permission_classes = [IsAuthenticatedActive, IsAdminOrSuper]

    @extend_schema(
        summary="List Phones",
        description="Retrieve a list of phones, filtered by user role.",
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
        description="Create a new phone and link to a contact (ADMIN or SUPER only).",
        request=PhoneSerializer,
        responses={
            201: PhoneSerializer,
            400: OpenApiResponse(description="Invalid data"),
            401: OpenApiResponse(description="Unauthorized"),
            403: OpenApiResponse(description="Forbidden"),
        }
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.save()
        contact_id = request.data.get('contact_id')
        if contact_id:
            try:
                contact = Contact.objects.get(id=contact_id)
                contact.refs.setdefault('phones', []).append(str(phone.id))
                contact.save()
            except Contact.DoesNotExist:
                phone.delete()
                return Response({"contact_id": "Invalid contact ID"}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class PhoneDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Handles retrieving, updating, and deleting a phone."""
    queryset = Phone.objects.all()
    serializer_class = PhoneSerializer
    permission_classes = [IsAuthenticatedActive, IsAdminOrSuper]

    @extend_schema(
        summary="Get Phone",
        description="Retrieve a specific phone by ID, filtered by user role.",
        responses={
            200: PhoneSerializer,
            401: OpenApiResponse(description="Unauthorized"),
            404: OpenApiResponse(description="Not found"),
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Update Phone",
        description="Update a phone (partial update, ADMIN/SUPER only).",
        request=PhoneSerializer,
        responses={
            200: PhoneSerializer,
            400: OpenApiResponse(description="Invalid data"),
            401: OpenApiResponse(description="Unauthorized"),
            404: OpenApiResponse(description="Not found"),
        }
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @extend_schema(
        summary="Delete Phone",
        description="Delete a phone and remove from contact refs (ADMIN/SUPER only).",
        responses={
            204: OpenApiResponse(description="Successfully deleted"),
            401: OpenApiResponse(description="Unauthorized"),
            404: OpenApiResponse(description="Not found"),
        }
    )
    def delete(self, request, *args, **kwargs):
        phone = self.get_object()
        Contact.objects.filter(refs__phones__contains=[str(phone.id)]).update(
            **{'refs.phones': models.F('refs__phones').exclude(str(phone.id))}
        )
        return super().delete(request, *args, **kwargs)