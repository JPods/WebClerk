"""Field rules for one model, optionally for one record.

GET /wcapi/<model_name>/fields/?id=<pk>

Returns what this user may see and change, by role (wc:view_edit Settings), and —
when an id is given — what the record's own state locks:

    {"view": [...], "edit": [...], "locked": [...], "is_locked": bool}

A journalized document locks its total and the values that make it up. Cash,
comments and operational fields stay editable (Bill, 2026-09-17). The UI shows a
field that is viewable but not editable with an italic label.
"""
from __future__ import annotations

from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from common.api_responses import api_response

# Envelopes whose numbers feed a journalized document's totals.
JOURNALIZED_LOCKED = ('totals', 'quantity', 'price', 'cost', 'tax', 'commission')


def locked_fields_for(record) -> list:
    """The fields this record's own state locks. Empty when nothing is locked."""
    if record is None or not getattr(record, 'is_locked', False):
        return []
    return [name for name in JOURNALIZED_LOCKED if hasattr(record, name)]


class FieldRulesView(APIView):
    """What this user may see and change on a model, and what the record locks.

    Reports the RBAC rules the API actually enforces (contact.refs.roles →
    role_defaults / RoleConfig → field_projection), not the wc:view_edit Settings
    path, which has no rows in production. Reporting rules nobody enforces would
    make the UI lie.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, model_name: str):
        from apps.core.services.role_filter import get_allowed_fields, get_denied_fields
        from apps.core.utils import registry

        model = registry.resolve(model_name)
        if model is None:
            return api_response(success=False, status_code=400,
                                message=f"unknown model: {model_name}",
                                error={"code": "unknown_model"})

        user = request.user
        view_fields = get_allowed_fields(user, model_name, mode="view")
        edit_fields = get_allowed_fields(user, model_name, mode="edit")
        denied = get_denied_fields(user, model_name)

        record = None
        record_id = request.query_params.get('id')
        if record_id:
            record = model._default_manager.filter(pk=record_id).first()
            if record is None:
                return api_response(success=False, status_code=404,
                                    message=f"{model_name} {record_id} not found",
                                    error={"code": "not_found"})

        locked = locked_fields_for(record)
        if locked and isinstance(edit_fields, list):
            if edit_fields == ["*"]:
                # everything except what the record locks
                edit_fields = ["*"]
                denied_edit = locked
            else:
                edit_fields = [f for f in edit_fields
                               if f not in locked and f.split('.')[0] not in locked]
                denied_edit = locked
        else:
            denied_edit = []

        return api_response(data={
            'model_name': model_name,
            'id': record.pk if record is not None else None,
            'view': view_fields,
            'view_deny': denied,
            'edit': edit_fields,
            'edit_deny': denied_edit,
            'locked': locked,
            'is_locked': bool(record is not None and getattr(record, 'is_locked', False)),
            'source': 'rbac',
        })
