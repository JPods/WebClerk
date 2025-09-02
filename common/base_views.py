from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from common.mixins import OptimisticPatchMixin
from common.models import VersionConflictError
from common.api_responses import api_response


class BaseListCreateView(generics.ListCreateAPIView):
    """Uniform list/create view with optional role gating.

    Subclasses can set ALLOWED_ROLES set; if empty, allow all authenticated.
    """
    permission_classes = [IsAuthenticated]
    ALLOWED_ROLES: set[str] | None = None
    ordering = '-modified_dt'

    def _role_allowed(self, user):
        if not user.is_authenticated:
            return False
        if not self.ALLOWED_ROLES:
            return True
        return getattr(user, 'role', '') in self.ALLOWED_ROLES or getattr(user, 'is_superuser', False)

    def get_queryset(self):
        qs = super().get_queryset()
        if not self._role_allowed(self.request.user):
            return qs.none()
        ordering = self.request.GET.get('ordering') or self.ordering
        if ordering:
            return qs.order_by(ordering)
        return qs

    def create(self, request, *args, **kwargs):
        if not self._role_allowed(request.user):
            return api_response(success=False, status_code=403, message='Forbidden', error={'code':'forbidden','details':'Forbidden'})
        resp = super().create(request, *args, **kwargs)
        # DRF returns serializer.data. Wrap into envelope with data.record for consistency.
        return api_response(data=resp.data, status_code=resp.status_code)

    def list(self, request, *args, **kwargs):  # wrap list responses
        resp = super().list(request, *args, **kwargs)
        if isinstance(resp.data, dict):
            results = resp.data.get('results')
            if results is None:
                # Attempt DRF pagination structures
                results = resp.data.get('results') or resp.data.get('data') or []
            count = resp.data.get('count')
            if count is None and isinstance(results, list):
                count = len(results)
            wrapped = {'results': results, 'count': count}
        else:
            wrapped = {'results': resp.data, 'count': len(resp.data) if isinstance(resp.data, list) else 1}
        return api_response(data=wrapped, status_code=resp.status_code)


class BaseOptimisticDetailView(OptimisticPatchMixin, generics.RetrieveUpdateDestroyAPIView):
    """Detail view with optimistic concurrency + atomic JSON patch.

    Usage: subclass and define queryset, serializer_class, optional ALLOWED_ROLES.
    """
    permission_classes = [IsAuthenticated]
    ALLOWED_ROLES: set[str] | None = None
    atomic_keys = ('set', 'append')

    def _role_allowed(self, user):
        if not user.is_authenticated:
            return False
        if not self.ALLOWED_ROLES:
            return True
        return getattr(user, 'role', '') in self.ALLOWED_ROLES or getattr(user, 'is_superuser', False)

    def get_queryset(self):
        qs = super().get_queryset()
        if not self._role_allowed(self.request.user):
            return qs.none()
        return qs

    def patch(self, request, *args, **kwargs):
        if not self._role_allowed(request.user):
            return api_response(success=False, status_code=403, message='Forbidden', error={'code':'forbidden','details':'Forbidden'})
        obj = self.get_object()
        data = request.data or {}
        if any(k in data for k in self.atomic_keys):
            try:
                updated = self.apply_atomic_ops(obj, data)
            except VersionConflictError as e:
                return api_response(success=False, status_code=412, message=str(e), error={'code':'version_conflict','details':str(e)})
            ser = self.get_serializer(updated)
            return api_response(data=ser.data, status_code=200)
        expected_version = data.get('version')
        if expected_version is not None and expected_version != obj.version:
            msg = f'Version conflict: expected {expected_version} got {obj.version}'
            return api_response(success=False, status_code=412, message=msg, error={'code':'version_conflict','details':msg})
        resp = super().patch(request, *args, **kwargs)
        return api_response(data=resp.data, status_code=resp.status_code)

    def retrieve(self, request, *args, **kwargs):
        resp = super().retrieve(request, *args, **kwargs)
        return api_response(data=resp.data, status_code=resp.status_code)

    def destroy(self, request, *args, **kwargs):
        resp = super().destroy(request, *args, **kwargs)
        # Some destroys return no content; unify to success with code 204
        return api_response(data=None, status_code=resp.status_code)