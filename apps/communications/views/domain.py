# filepath: /Users/williamjames/Documents/CommerceExpert/webClerk3/communications/views/domain.py
from rest_framework import generics, status, pagination, permissions
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiResponse
from ..serializers import DomainSerializer
from ..models import Domain
from apps.core.models import Contact
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.db import models
from apps.core.utils import get_accessible_fields
from common.models import default_refs  # ✅ ADD THIS IMPORT

class CommPagination(pagination.PageNumberPagination):
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 500


class DomainView(generics.ListCreateAPIView):
    """Handles listing and creating domains restricted to staff/admin/superuser; field-level filtering optional."""
    queryset = Domain.objects.all()
    serializer_class = DomainSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CommPagination
    ALLOWED_ROLES = {'staff','admin'}

    def _role_allowed(self, user):
        return getattr(user, 'role', '') in self.ALLOWED_ROLES or getattr(user, 'is_superuser', False)

    def get_queryset(self):
        if not self._role_allowed(self.request.user):
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
        if not self._role_allowed(request.user):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

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
    """Retrieve/update/delete domain restricted to staff/admin/superuser."""
    queryset = Domain.objects.all()
    serializer_class = DomainSerializer
    permission_classes = [IsAuthenticated]
    ALLOWED_ROLES = {'staff','admin'}

    def _role_allowed(self, user):
        return getattr(user, 'role', '') in self.ALLOWED_ROLES or getattr(user, 'is_superuser', False)

    def get_queryset(self):
        if not self._role_allowed(self.request.user):
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
        if not self._role_allowed(request.user):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
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
        if not self._role_allowed(request.user):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

        domain = self.get_object()
        Contact.objects.filter(refs__domains__contains=[str(domain.id)]).update(
            **{'refs__domains': models.F('refs__domains').exclude(str(domain.id))}
        )
        return super().delete(request, *args, **kwargs)
    

class DomainSearchView(APIView):
    """Multi-term AND prefix search restricted to staff/admin/superuser."""
    permission_classes = [permissions.IsAuthenticated]
    ALLOWED_ROLES = {'staff', 'admin'}

    def get(self, request):
        user = request.user
        if not (getattr(user, 'role', '') in self.ALLOWED_ROLES or user.is_superuser):
            return Response({'detail': 'Forbidden'}, status=403)
        raw_q = (request.GET.get('q') or '').strip()
        if not raw_q:
            return Response({'results': [], 'count': 0, 'q': raw_q})
        terms = [t for t in raw_q.split() if t]
        qs = Domain.objects.filter(is_active=True)
        status_val = request.GET.get('status')
        if status_val:
            qs = qs.filter(status=status_val)
        level = request.GET.get('security_level') or request.GET.get('level')
        if level is not None:
            try:
                qs = qs.filter(security_level=int(level))
            except ValueError:
                pass
        for term in terms:
            qs = qs.filter(
                models.Q(path__istartswith=term) | models.Q(type__istartswith=term) | models.Q(comment__istartswith=term)
            )
        qs = qs.order_by('-modified_dt')[:100]
        data = DomainSerializer(qs, many=True, context={'request': request}).data
        for d in qs:
            d.increment_access(by=1, save=True)
        return Response({'results': data, 'count': len(data), 'q': raw_q, 'terms': terms})
    

