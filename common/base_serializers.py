from rest_framework import serializers
from apps.core.utils import get_accessible_fields


class RoleAwareModelSerializer(serializers.ModelSerializer):
    """Base serializer enforcing role-based field visibility/edit rules.

    Uses settings-driven matrices (view_edit) via get_accessible_fields(table, mode, user).
    Subclasses should define Meta.model & Meta.fields normally; set model_name when needed.
    """
    model_name: str | None = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if not request or not getattr(request, 'user', None) or not request.user.is_authenticated:
            return
        mode = 'edit' if request.method in ['POST','PATCH','PUT'] else 'view'
        meta = getattr(self, 'Meta', None)
        model = getattr(meta, 'model', None) if meta else None
        model_name = self.model_name or (model.__name__ if model is not None else '')
        allowed = get_accessible_fields(model_name or '', mode, request.user)
        privileged = getattr(request.user, 'role', '') in {'staff','admin'} or getattr(request.user, 'is_superuser', False)
        if allowed:
            for f in set(self.fields) - set(allowed):
                self.fields.pop(f, None)
        elif not privileged:
            minimal = {'id','uuid'}
            for f in list(self.fields.keys()):
                if f not in minimal:
                    self.fields.pop(f, None)
