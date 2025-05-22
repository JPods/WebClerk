from rest_framework import permissions

class HasRole(permissions.BasePermission):
    def __init__(self, allowed_roles):
        super().__init__()
        self.allowed_roles = allowed_roles

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and any(role in self.allowed_roles for role in request.user.role)