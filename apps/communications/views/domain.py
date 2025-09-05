# path: apps/communications/views/domain.py
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
from common.models import default_refs, VersionConflictError  # ✅ ADD THIS IMPORT
from rest_framework.exceptions import ValidationError
from common.mixins import OptimisticPatchMixin
from common.api_responses import api_response

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
        raw_flag = request.query_params.get('raw') == '1'
        response = super().get(request, *args, **kwargs)
        if raw_flag:
            return response
        data = response.data
        meta = {}
        if isinstance(data, dict) and {'results','count'}.issubset(data.keys()):
            meta = {
                'total': data.get('count'),
                'page_size': request.query_params.get('page_size') or CommPagination.page_size,
                'next': data.get('next'),
                'previous': data.get('previous')
            }
            results = data.get('results')
        else:
            results = data
        payload = {'results': results}
        payload.update({k: v for k, v in meta.items() if v is not None})
        return api_response(data=payload, raw=raw_flag)

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
        raw_flag = request.query_params.get('raw') == '1'
        if not self._role_allowed(request.user):
            return api_response(success=False, status_code=status.HTTP_403_FORBIDDEN, message="Forbidden", error={'code':'forbidden'}, raw=raw_flag)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        domain = serializer.save()
        if not domain.refs:
            domain.refs = default_refs()
        domain.refs.setdefault('links', {}).setdefault('contacts', [])
        if request.user.id not in domain.refs['links']['contacts']:
            domain.refs['links']['contacts'].append(request.user.id)
        domain.save()
        if raw_flag:
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return api_response(data=serializer.data, status_code=status.HTTP_201_CREATED, raw=raw_flag)


class DomainDetailView(OptimisticPatchMixin, generics.RetrieveUpdateDestroyAPIView):
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
        raw_flag = request.query_params.get('raw') == '1'
        response = super().get(request, *args, **kwargs)
        if raw_flag:
            return response
        return api_response(data=response.data, raw=raw_flag)

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
        raw_flag = request.query_params.get('raw') == '1'
        if not self._role_allowed(request.user):
            return api_response(success=False, status_code=403, message="Forbidden", error={'code':'forbidden'}, raw=raw_flag)
        obj = self.get_object()
        payload = request.data or {}
        if any(k in payload for k in ('set','append')):
            try:
                updated = self.apply_atomic_ops(obj, payload)
            except VersionConflictError as e:
                return api_response(success=False, status_code=412, message='Version conflict', error={'detail': str(e), 'code':'version_conflict'}, raw=raw_flag)
            except ValidationError as ve:
                if raw_flag:
                    return Response(ve.detail, status=400)
                return api_response(success=False, status_code=400, message='Validation error', error={'fields': ve.detail}, raw=raw_flag)
            ser = self.get_serializer(updated)
            if raw_flag:
                return Response(ser.data, status=200)
            return api_response(data=ser.data, raw=raw_flag)
        expected_version = payload.get('version')
        if expected_version is not None and expected_version != obj.version:
            return api_response(success=False, status_code=412, message='Version conflict', error={'expected': expected_version, 'current': obj.version, 'code': 'version_conflict'}, raw=raw_flag)
        response = super().patch(request, *args, **kwargs)
        if raw_flag:
            return response
        return api_response(data=response.data, raw=raw_flag)

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
        raw_flag = request.query_params.get('raw') == '1'
        if not self._role_allowed(request.user):
            return api_response(success=False, status_code=403, message="Forbidden", error={'code':'forbidden'}, raw=raw_flag)
        # Relationship cleanup: remove domain id from any contact refs.links.domains lists if present.
        domain = self.get_object()
        # Fetch contacts referencing this domain id (stored as string) in refs.links.domains
        contacts = Contact.objects.filter(refs__links__domains__contains=[domain.id])
        for c in contacts:
            try:
                domains_list = c.refs.get('links', {}).get('domains', [])
                new_list = [d for d in domains_list if str(d) != str(domain.id)]
                if new_list != domains_list:
                    c.refs.setdefault('links', {})['domains'] = new_list
                    c.save(update_fields=['refs', 'dt_modified'])
            except Exception:  # defensive; do not block delete on malformed refs
                pass
        response = super().delete(request, *args, **kwargs)
        if raw_flag:
            return response
        return api_response(message='Deleted', data=None, status_code=200, raw=raw_flag)
    

class DomainSearchView(APIView):
    """Multi-term AND prefix search restricted to staff/admin/superuser."""
    permission_classes = [permissions.IsAuthenticated]
    ALLOWED_ROLES = {'staff', 'admin'}

    def get(self, request):
        raw_flag = request.query_params.get('raw') == '1'
        user = request.user
        if not (getattr(user, 'role', '') in self.ALLOWED_ROLES or user.is_superuser):
            return api_response(success=False, status_code=403, message='Forbidden', error={'code':'forbidden'}, raw=raw_flag)
        raw_q = (request.GET.get('q') or '').strip()
        if not raw_q:
            empty_payload = {'results': [], 'count': 0, 'q': raw_q, 'terms': []}
            if raw_flag:
                return Response(empty_payload)
            return api_response(data=empty_payload, raw=raw_flag)
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
        qs = qs.order_by('-dt_modified')[:100]
        data = DomainSerializer(qs, many=True, context={'request': request}).data
        for d in qs:
            d.increment_access(by=1, save=True)
        payload = {'results': data, 'count': len(data), 'q': raw_q, 'terms': terms}
        if raw_flag:
            return Response(payload)
        return api_response(data=payload, raw=raw_flag)
    

