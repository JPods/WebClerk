from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from common.mixins import OptimisticPatchMixin
from common.models import VersionConflictError


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
            return Response({'detail': 'Forbidden'}, status=403)
        return super().create(request, *args, **kwargs)


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
            return Response({'detail': 'Forbidden'}, status=403)
        obj = self.get_object()
        data = request.data or {}
        if any(k in data for k in self.atomic_keys):
            try:
                updated = self.apply_atomic_ops(obj, data)
            except VersionConflictError as e:
                return Response({'detail': str(e), 'code': 'version_conflict'}, status=409)
            from rest_framework import status as drf_status
            return Response(self.get_serializer(updated).data, status=drf_status.HTTP_200_OK)
        expected_version = data.get('version')
        if expected_version is not None and expected_version != obj.version:
            return Response({'detail': f'Version conflict: expected {expected_version} got {obj.version}', 'code': 'version_conflict'}, status=409)
        return super().patch(request, *args, **kwargs)