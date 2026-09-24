from __future__ import annotations
from django.db.models import QuerySet
from typing import List, Optional


def _org_scope_q(model_fields: set[str], user) -> Optional["Q"]:
    """Build org-based visibility constraints derived from the user's org associations."""
    try:
        from django.db.models import Q  # local import to avoid hard dependency at module import
    except Exception:
        return None

    org_field_names = {
        "org_id",
        "organization_id",
        "customer_id",
        "vendor_id",
        "manufacturer_id",
        "rep_id",
        "employee_id",
        "other_id",
    }

    # Capture user org pointers from Contact fields when present
    user_org_ids: dict[str, int] = {}
    for name in org_field_names:
        val = getattr(user, name.replace("_id", "_id"), None)
        if isinstance(val, int):
            user_org_ids[name] = val

    if not user_org_ids:
        return None

    clauses = []
    for field in org_field_names:
        if field in model_fields and field in user_org_ids:
            clauses.append(Q(**{field: user_org_ids[field]}))

    if not clauses:
        return None

    scope = clauses[0]
    for clause in clauses[1:]:
        scope |= clause
    return scope


def inject_constraints(qs: QuerySet, *, actor, model_key: str) -> QuerySet:
    """Enforce tenant isolation and strict role-based visibility.

    Takes the actor, not the request: the get and delete doors are called by writers and
    readers that have no request (Bill, 2026-09-22 — one channel per verb). Applies to a
    person only: a system actor is unguarded, and a sync actor's rows are its Connection's
    role scope (gates 2–3), not a login's org pointers.
    """
    from apps.core.services.door import as_actor
    actor = as_actor(actor)
    if not actor.is_guarded or actor.kind == 'sync':
        return qs
    if actor.kind == 'public':
        return qs.none()
    user = actor.user
    try:
        from django.conf import settings
        from django.db.models import Q

        if not user or not user.is_authenticated:
            return qs.none()

        role_value = getattr(user, 'role', None)
        user_role = str(role_value).lower() if role_value else None

        # Admin/staff/full-control roles: unrestricted
        if getattr(user, 'is_superuser', False) or getattr(user, 'is_staff', False) or user_role == 'admin':
            return qs

        constraints = Q()

        # Tenant isolation first
        multi_tenant_enabled = getattr(settings, 'WCAPI_MULTI_TENANT_ENABLED', False)
        tenant_field = getattr(settings, 'WCAPI_TENANT_FIELD', 'tenant_id')
        if multi_tenant_enabled and hasattr(user, 'tenant_id'):
            constraints &= Q(**{tenant_field: getattr(user, 'tenant_id')})

        fields = {f.name for f in qs.model._meta.get_fields()}

        # Org-based scoping for employees and users (must be linked to an org profile)
        org_scope = _org_scope_q(fields, user)
        if org_scope is not None:
            constraints &= org_scope

        # Employees: after org scoping, allow ownership-like access as well
        if user_role == 'employee':
            ownership_clauses = []
            if 'created_by' in fields:
                ownership_clauses.append(Q(created_by=getattr(user, 'id', None)))
            if 'contact' in fields:
                ownership_clauses.append(Q(contact_id=getattr(user, 'id', None)))
            if 'owner' in fields:
                ownership_clauses.append(Q(owner_id=getattr(user, 'id', None)))
            if 'assigned_to' in fields:
                ownership_clauses.append(Q(assigned_to_id=getattr(user, 'id', None)) | Q(assigned_to=user))
            if 'assignee' in fields:
                ownership_clauses.append(Q(assignee_id=getattr(user, 'id', None)) | Q(assignee=user))
            if ownership_clauses:
                scope = ownership_clauses[0]
                for clause in ownership_clauses[1:]:
                    scope |= clause
                constraints &= scope
            if constraints:
                qs = qs.filter(constraints).distinct()
            return qs

        # User-level scope: own or explicitly assigned records
        ownership_clauses = []
        model_name = getattr(qs.model._meta, 'model_name', '')

        # Transaction models: customer_id and contact_id on transactions are org/party FKs,
        # not ownership fields. RBAC inject_role_filters handles org-level scoping
        # via $user.org_ids. Skip ownership clauses entirely for transaction models.
        transaction_models = {
            'quote', 'order', 'invoice', 'purchase', 'workorder',
            'quoteline', 'orderline', 'invoiceline', 'purchaseline', 'workorderline',
            'document', 'item', 'setting',
        }
        is_txn = model_name.lower() in transaction_models

        if not is_txn:
            if 'created_by' in fields:
                ownership_clauses.append(Q(created_by=getattr(user, 'id', None)))
            if 'contact' in fields:
                ownership_clauses.append(Q(contact_id=getattr(user, 'id', None)))
            if 'owner' in fields:
                ownership_clauses.append(Q(owner_id=getattr(user, 'id', None)))
            if 'user' in fields:
                ownership_clauses.append(Q(user_id=getattr(user, 'id', None)))
            if 'assigned_to' in fields:
                ownership_clauses.append(Q(assigned_to_id=getattr(user, 'id', None)) | Q(assigned_to=user))
            if 'assignee' in fields:
                ownership_clauses.append(Q(assignee_id=getattr(user, 'id', None)) | Q(assignee=user))
            if 'shared_with' in fields:
                ownership_clauses.append(Q(shared_with__id=getattr(user, 'id', None)))
            if 'customer_id' in fields and model_name.lower() != 'contact':
                ownership_clauses.append(Q(customer_id=getattr(user, 'id', None)))

        # Transaction models without ownership fields: allow all for authenticated users
        # These are business documents that employees need to access
        org_models = {
            'org',
            'orgbase',
            'customer',
            'vendor',
            'manufacturer',
            'rep',
            'employee',
        }
        # Contact records are business data that employees need to look up
        # by FK (customer_id, vendor_id, etc.) — treat like transaction models.
        contact_models = {'contact'}

        is_transaction_model = model_name.lower() in transaction_models
        is_org_model = model_name.lower() in org_models
        is_contact_model = model_name.lower() in contact_models

        if ownership_clauses:
            scope = ownership_clauses[0]
            for clause in ownership_clauses[1:]:
                scope |= clause
            constraints &= scope
        elif is_transaction_model or is_org_model or is_contact_model:
            # Transaction/org/contact models: authenticated users can access all records
            # (org-level scoping already applied above if enabled)
            pass
        elif not is_contact_model:
            # No ownership-related fields and not contact/transaction; safest default is no access
            constraints &= Q(pk__in=[])

        if constraints:
            qs = qs.filter(constraints).distinct()
        return qs

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Error applying settings constraints for {model_key}: {str(e)}")
        return qs
