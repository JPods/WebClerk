from rest_framework import generics, status
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiResponse
from ..serializers import DomainSerializer
from ..models import Domain
from core.models import Contact
from core.permissions import IsAuthenticatedActive, IsAdminOrSuper

class DomainView(generics.ListCreateAPIView):
    """Handles listing and creating domains."""
    queryset = Domain.objects.all()
    serializer_class = DomainSerializer
    permission_classes = [IsAuthenticatedActive, IsAdminOrSuper]

    @extend_schema(
        summary="List Domains",
        description="Retrieve a list of domains, filtered by user role.",
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
        description="Create a new domain and link to a contact (ADMIN or SUPER only).",
        request=DomainSerializer,
        responses={
            201: DomainSerializer,
            400: OpenApiResponse(description="Invalid data"),
            401: OpenApiResponse(description="Unauthorized"),
            403: OpenApiResponse(description="Forbidden"),
        }
    )

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        domain = serializer.save()
        contact_id = request.data.get('contact_id')
        if contact_id:
            try:
                contact = Contact.objects.get(id=contact_id)
                contact.refs.setdefault('domains', []).append(str(domain.id))
                contact.save()
            except Contact.DoesNotExist:
                domain.delete()
                return Response({"contact_id": "Invalid contact ID"}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class DomainDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Handles retrieving, updating, and deleting a domain."""
    queryset = Domain.objects.all()
    serializer_class = DomainSerializer
    permission_classes = [IsAuthenticatedActive, IsAdminOrSuper]

    @extend_schema(
        summary="Get Domain",
        description="Retrieve a specific domain by ID, filtered by user role.",
        responses={
            200: DomainSerializer,
            401: OpenApiResponse(description="Unauthorized"),
            404: OpenApiResponse(description="Not found"),
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Update Domain",
        description="Update a domain (partial update, ADMIN/SUPER only).",
        request=DomainSerializer,
        responses={
            200: DomainSerializer,
            400: OpenApiResponse(description="Invalid data"),
            401: OpenApiResponse(description="Unauthorized"),
            404: OpenApiResponse(description="Not found"),
        }
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @extend_schema(
        summary="Delete Domain",
        description="Delete a domain and remove from contact refs (ADMIN/SUPER only).",
        responses={
            204: OpenApiResponse(description="Successfully deleted"),
            401: OpenApiResponse(description="Unauthorized"),
            404: OpenApiResponse(description="Not found"),
        }
    )
    def delete(self, request, *args, **kwargs):
        domain = self.get_object()
        Contact.objects.filter(refs__domains__contains=[str(domain.id)]).update(
            **{'refs.domains': models.F('refs__domains').exclude(str(domain.id))})
        return super().delete(request, *args, **kwargs)