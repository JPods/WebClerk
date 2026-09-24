"""Field rules for one model, optionally for one record.

GET /wcapi/<model_name>/fields/?id=<pk>

Returns what this user may see and change, by role (the model's wc:model Setting), and —
when an id is given — what the record's own state locks:

    {"view": [...], "edit": [...], "locked": [...], "is_locked": bool}

A journalized document locks its total and the values that make it up. Cash,
comments and operational fields stay editable (Bill, 2026-09-17). The UI shows a
field that is viewable but not editable with an italic label.
"""
from __future__ import annotations
from apps.core.services.door import Actor

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

    Reports the rules the API enforces: the role's positive lists in the model's
    wc:model Setting (apps/core/services/access.py).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, model_name: str):
        from apps.core.services.role_filter import get_allowed_fields
        from apps.core.utils import registry

        model = registry.resolve(model_name)
        if model is None:
            return api_response(success=False, status_code=400,
                                message=f"unknown model: {model_name}",
                                error={"code": "unknown_model"})

        user = request.user
        actor = Actor.from_request(request)
        view_fields = get_allowed_fields(actor, model_name, mode="view")
        edit_fields = get_allowed_fields(actor, model_name, mode="edit")

        record = None
        record_id = request.query_params.get('id')
        if record_id:
            record = model._default_manager.filter(pk=record_id).first()
            if record is None:
                return api_response(success=False, status_code=404,
                                    message=f"{model_name} {record_id} not found",
                                    error={"code": "not_found"})

        locked = locked_fields_for(record)
        if locked:
            edit_fields = [f for f in edit_fields if f.split('.')[0] not in locked]
            denied_edit = locked
        else:
            denied_edit = []

        return api_response(data={
            'model_name': model_name,
            'id': record.pk if record is not None else None,
            'view': view_fields,
            'edit': edit_fields,
            'edit_deny': denied_edit,
            'locked': locked,
            'is_locked': bool(record is not None and getattr(record, 'is_locked', False)),
            'source': 'rbac',
        })
