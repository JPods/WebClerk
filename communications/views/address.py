from rest_framework import generics, status
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiResponse
from ..serializers import AddressSerializer
from ..models import Address
from core.models import Contact
from core.permissions import IsAuthenticatedActive, IsAdminOrSuper

class AddressView(generics.ListCreateAPIView):
    """Handles listing and creating addresses."""
    queryset = Address.objects.all()
    serializer_class = AddressSerializer
    permission_classes = [IsAuthenticatedActive, IsAdminOrSuper]

    @extend_schema(
        summary="List Addresses",
        description="Retrieve a list of addresses, filtered by user role.",
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
        description="Create a new address and link to a contact (ADMIN or SUPER only).",
        request=AddressSerializer,
        responses={
            201: AddressSerializer,
            400: OpenApiResponse(description="Invalid data"),
            401: OpenApiResponse(description="Unauthorized"),
            403: OpenApiResponse(description="Forbidden"),
        }
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        address = serializer.save()
        # Link to contact if provided
        contact_id = request.data.get('contact_id')
        if contact_id:
            try:
                contact = Contact.objects.get(id=contact_id)
                contact.refs.setdefault('addresses', []).append(str(address.id))
                contact.save()
            except Contact.DoesNotExist:
                address.delete()
                return Response({"contact_id": "Invalid contact ID"}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class AddressDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Handles retrieving, updating, and deleting an address."""
    queryset = Address.objects.all()
    serializer_class = AddressSerializer
    permission_classes = [IsAuthenticatedActive, IsAdminOrSuper]

    @extend_schema(
        summary="Get Address",
        description="Retrieve a specific address by ID, filtered by user role.",
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
        description="Update an address (partial update, ADMIN/SUPER only).",
        request=AddressSerializer,
        responses={
            200: AddressSerializer,
            400: OpenApiResponse(description="Invalid data"),
            401: OpenApiResponse(description="Unauthorized"),
            404: OpenApiResponse(description="Not found"),
        }
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @extend_schema(
        summary="Delete Address",
        description="Delete an address and remove from contact refs (ADMIN/SUPER only).",
        responses={
            204: OpenApiResponse(description="Successfully deleted"),
            401: OpenApiResponse(description="Unauthorized"),
            404: OpenApiResponse(description="Not found"),
        }
    )
    def delete(self, request, *args, **kwargs):
        address = self.get_object()
        # Remove from contact refs
        Contact.objects.filter(refs__addresses__contains=[str(address.id)]).update(
            **{'refs.addresses': models.F('refs__addresses').exclude(str(address.id))}
        )
        return super().delete(request, *args, **kwargs)