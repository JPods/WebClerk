from functools import lru_cache
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.permissions import BasePermission, SAFE_METHODS
from apps.core.models.setting import Setting
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from apps.core.services.wcapi_registry import to_model_name


@lru_cache(maxsize=256)
def _cached_view_edit_matrix(setting_id: int, dt_modified: str):
    try:
        s = Setting.objects.only('data').get(id=setting_id)
    except Setting.DoesNotExist:
        return {}
    return s.data or {}


def _get_active_view_edit_setting(model_name: str) -> tuple[int | None, dict]:
    """Return (setting_id, matrix) for active view_edit rule by canonical model_name.

    Strict lookup on Setting(model_name=...). Returns (None, {}) if no active rule so
    callers can deny by default.
    """
    try:
        s = (Setting.objects
             .filter(purpose='view_edit', model_name=model_name, is_active=True)
             .order_by('-dt_modified')
             .only('id', 'data', 'dt_modified')
             .first())
        if not s:
            return None, {}
        matrix = _cached_view_edit_matrix(s.id, str(s.dt_modified))
        return s.id, matrix
    except ObjectDoesNotExist:  # pragma: no cover
        return None, {}


class ViewEditPermission(BasePermission):
    """Permission enforcing field-level view/edit capability based on Setting.data matrix.

    Setting format example (Setting.purpose='view_edit'):
    data = {
      "ADMIN": {"view": ["id", "email"], "edit": ["email"]},
      "USER": {"view": ["id"], "edit": []}
    }
    A role can view or edit only if field is listed. For endpoint-level access we just require
    at least one allowed field for the intended operation (view vs edit). Fine-grained per-field
    validation can be enforced elsewhere (e.g., serializer validation) if needed later.
    """

    def has_permission(self, request, view):  # endpoint-level gate
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return False
        queryset = getattr(view, 'queryset', None)
        model = getattr(queryset, 'model', None)
        if model is None:
            return True  # nothing to enforce
        # Resolve canonical model_name from db_table (registry-backed)
        model_name = to_model_name(model._meta.db_table)

        _, matrix = _get_active_view_edit_setting(model_name or '')
        if not matrix:
            return False  # secure default: no active rules

        role = getattr(user, 'role', None)
        role_key = (role or '').upper()
        role_rules = matrix.get(role_key) or matrix.get('PUBLIC') or {}
        op = 'view' if request.method in SAFE_METHODS else 'edit'
        allowed_fields = role_rules.get(op, [])
        return bool(allowed_fields)  # require at least one field permitted

    def has_object_permission(self, request, view, obj):
        # For now mirror has_permission; object-level field restrictions can be layered later.
        return self.has_permission(request, view)

def get_role_field_rules(model, role: str) -> dict:
    model_name = to_model_name(model._meta.db_table)
    _, matrix = _get_active_view_edit_setting(model_name or '')
    if not matrix:
        return {"view": [], "edit": []}
    role_key = (role or '').upper()
    role_rules = matrix.get(role_key) or matrix.get('PUBLIC') or {}
    return {"view": role_rules.get('view', []), "edit": role_rules.get('edit', [])}


@receiver([post_save, post_delete], sender=Setting)
def clear_view_edit_cache(sender, instance, **kwargs):  # pragma: no cover (simple invalidation)
    if instance.purpose == 'view_edit':
        _cached_view_edit_matrix.cache_clear()
