from rest_framework import serializers
import uuid
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

    # --- UUID policy at the API boundary ---
    # If this serializer is used in an API request and the model has a 'uuid' field that is currently null,
    # assign a UUIDv4. This keeps UUIDs optional internally but ensures externalized records gain stable IDs.
    def _ensure_uuid_if_api(self, instance):
        try:
            request = self.context.get('request')
        except Exception:
            request = None
        if not request:
            return instance
        if not hasattr(instance, 'uuid'):
            return instance
        if getattr(instance, 'uuid', None) is None:
            # Assign v4 by default at the API boundary
            try:
                instance.uuid = uuid.uuid4()
                instance.save(update_fields=['uuid'])
            except Exception:
                # Best-effort: if update fails, leave as-is and let endpoint surface errors if needed
                pass
        return instance

    def create(self, validated_data):
        instance = super().create(validated_data)
        return self._ensure_uuid_if_api(instance)

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        return self._ensure_uuid_if_api(instance)

    # --- Commission data is internal-only ---
    # Non-staff users: remove the commission field entirely.
    # The cost and finance envelopes travel INTACT — never mutate JSON
    # envelopes in serialization (round-trip data loss on PATCH).

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        if request:
            user = getattr(request, 'user', None)
            is_staff = user and (
                getattr(user, 'is_staff', False) or getattr(user, 'is_superuser', False)
            )
            if not is_staff:
                data.pop('commission', None)
        return data
