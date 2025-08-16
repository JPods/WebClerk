# filepath: /Users/williamjames/Documents/CommerceExpert/webClerk3/core/permissions.py
from rest_framework import permissions

class IsAuthenticatedActive(permissions.BasePermission):
    """Allows access only to authenticated and active users."""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_active

class IsOwnerOrAdmin(permissions.BasePermission):
    """Allows access to the object owner or users with ADMIN/SUPER role."""
    def has_object_permission(self, request, view, obj):
        if request.user and request.user.is_authenticated:
            if hasattr(obj, 'email'):
                # For Contact objects
                return obj.email == request.user.email or any(role in request.user.role for role in ['ADMIN', 'SUPER'])
            return any(role in request.user.role for role in ['ADMIN', 'SUPER'])
        return False

class IsAdminOrSuper(permissions.BasePermission):
    """Allows access only to users with ADMIN or SUPER role."""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and any(role in request.user.role for role in ['ADMIN', 'SUPER'])