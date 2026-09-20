from __future__ import annotations
from typing import Any, Dict, List, Optional
from django.forms.models import model_to_dict
import logging
from django.db import IntegrityError
from django.db.models import QuerySet, Model

logger = logging.getLogger(__name__)
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from apps.core.utils import registry
from apps.core.services.role_filter import inject_role_filters, can_create, can_delete
from apps.core.services.field_projection import validate_user_edit

def to_dict(obj: Model) -> Dict[str, Any]:
    try:
        return model_to_dict(obj)
    except Exception:
        data: Dict[str, Any] = {}
        for f in getattr(obj._meta, "fields", []):
            try:
                data[f.name] = getattr(obj, f.name)
            except Exception:
                pass
        return data

def filter_input_fields(ModelCls: type[Model], payload: Dict[str, Any]) -> Dict[str, Any]:
    """Filter payload to model fields, normalising FK names to attname."""
    meta_fields = getattr(ModelCls._meta, "fields", [])
    allowed: Dict[str, str] = {}
    for f in meta_fields:
        attname = getattr(f, "attname", None)
        if attname and attname != f.name:
            allowed[f.name] = attname
            allowed[attname] = attname
        else:
            allowed[f.name] = f.name
    result: Dict[str, Any] = {}
    for k, v in (payload or {}).items():
        canonical = allowed.get(k)
        if canonical is not None:
            result[canonical] = v
    return result

def inject_constraints(qs: QuerySet, request, model_key: str) -> QuerySet:
    """Enforce role/tenant/publish/reserved constraints based on Settings.
    
    Args:
        qs: QuerySet to apply constraints to
        request: Django request object for user context
        model_key: Model key for specific constraint lookup
        
    Returns:
        QuerySet with applied constraints
    """
    try:
        from django.contrib.auth import get_user_model
        from django.conf import settings
        
        # Get user from request
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return qs.none()  # No access for unauthenticated users
            
        User = get_user_model()
        
        # Check if user is staff/admin - they get full access
        if hasattr(user, 'is_staff') and user.is_staff:
            return qs
        role_value = getattr(user, 'role', None)
        normalized_role = role_value.strip().lower() if isinstance(role_value, str) else None
        if normalized_role in {'staff', 'admin'}:
            return qs
            
        # Apply tenant isolation if multi-tenant setup
        tenant_field = getattr(settings, 'WCAPI_TENANT_FIELD', None)
        if tenant_field and hasattr(user, 'tenant_id'):
            qs = qs.filter(**{tenant_field: user.tenant_id})
            
        # Apply publish/reserved filtering based on user role
        if normalized_role:
            
            # Public users can only see published items
            if normalized_role in ['public', 'guest']:
                if 'is_published' in [f.name for f in qs.model._meta.get_fields()]:
                    qs = qs.filter(is_published=True)
                    
            # Reserved items only for authenticated users with proper role
            if 'is_reserved' in [f.name for f in qs.model._meta.get_fields()]:
                if normalized_role in ['admin', 'staff']:
                    # Admins can see both reserved and non-reserved
                    pass
                else:
                    # Regular users only see non-reserved items
                    qs = qs.filter(is_reserved=False)
                    
        # Apply model-specific constraints from settings
        model_constraints = getattr(settings, 'WCAPI_MODEL_CONSTRAINTS', {})
        if model_key in model_constraints:
            constraints = model_constraints[model_key]
            # Apply role-based constraints
            if 'role_filters' in constraints and normalized_role:
                role_filters = constraints['role_filters'].get(normalized_role, {})
                for field, filter_value in role_filters.items():
                    qs = qs.filter(**{field: filter_value})
                    
        return qs
        
    except Exception as e:
        # Log the error but don't break the query
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Error applying constraints for {model_key}: {str(e)}")
        return qs  # Return unfiltered queryset on error

TRANSACTION_MODELS_WITH_LINES = {
    "quote",
    "order",
    "invoice",
    "purchase",
    "workorder",
}

# Header fields a portal customer may supply; everything else is set by the server.
_PORTAL_ORDER_MODELS = {"order", "quote"}


def _leaf_paths(payload, prefix: str = "", collections: frozenset = frozenset()) -> set:
    """Every leaf path in a payload, dotted — the shape the enumeration speaks.

    ``{"totals": {"total": 10}}`` → ``{"totals.total"}``. A nested envelope is walked to
    its leaves because that is how access lists are written: "every path is a leaf"
    (access.py, Bill 2026-09-18).

    **A declared collection is walked too, with no index.** ``lines`` is not a leaf; it is
    a collection, and the enumeration already names what is inside it —
    ``lines.item.item_id``, ``lines.quantity.active`` (access.PORTAL_ORDER_FIELDS). Every
    element contributes its leaves under the one prefix, so a role is granted a line field
    once rather than per row. Walking only dicts left the bare key ``lines`` offered, which
    no list names and none should: the screen's save was refused for every role.

    ``collections`` is the set of keys this model accepts as objects, from
    ``field_leaves.collections`` — the same declaration the leaf map builds those paths
    from. **A list under any other key stays a leaf**, so an undeclared collection is
    offered as a bare key, named by no role, and refused. Fails closed.
    """
    out = set()
    for key, value in (payload or {}).items():
        path = f"{prefix}{key}"
        if isinstance(value, dict) and value:
            out |= _leaf_paths(value, f"{path}.")
        elif not prefix and key in collections and isinstance(value, list):
            for element in value:
                if isinstance(element, dict):
                    out |= _leaf_paths(element, f"{path}.")
        else:
            out.add(path)
    return out


def _collection_too_large(model_name: str, payload: dict):
    """The one refusal an enumeration cannot make.

    A positive list governs a payload's *shape* — which fields it may carry. It says
    nothing about its *size*, so a caller may name only permitted fields and still send
    a hundred thousand rows. Each collection declares its own cap beside it
    (``field_leaves.collections``), and this is checked before anything is walked or saved.

    Returns a message, or None. Kept separate from ``_not_enumerated`` deliberately: a
    caller sending too many rows has a different problem from one naming a field it may
    not write, and telling them the same thing wastes both their time.
    """
    from apps.core.services import field_leaves

    for key, (_child, max_rows) in field_leaves.collections(model_name).items():
        value = (payload or {}).get(key)
        if isinstance(value, list) and len(value) > max_rows:
            return (f"{key}: {len(value)} rows exceeds the {max_rows} this model accepts "
                    f"in one save")
    return None


#: Keys a client always sends that name the record rather than change it.
_IDENTITY_KEYS = frozenset({"id", "pk", "uuid", "ida", "model_name", "parent_model", "version"})

#: Keys that belong to the request envelope or the client's own bookkeeping, not to any
#: record. They are not fields, so the enumeration has nothing to say about them and a
#: positive list may not name them. ``options`` carries verify_calculations and
#: save_only_dirty; ``_dirty`` is the screen's marker for which lines it touched
#: (``saveTransactionWithLines``, frontend/src/api/wcapi.ts).
_ENVELOPE_KEYS = frozenset({"options", "_dirty"})

#: Everything that is not a field of the record being saved.
_NOT_A_FIELD = _IDENTITY_KEYS | _ENVELOPE_KEYS


def _not_enumerated(user, model_name: str, payload: dict, prefix: str = "") -> list:
    """Paths in this payload that the role's edit enumeration does not name.

    Access is an enumeration, not a filter (Bill, 2026-09-20): a filter answers "may you
    edit this thing", an enumeration answers "which parts of it". The block's ``edit``
    list is already set-expanded by access.resolve_roles, so it is the list itself.
    """
    from apps.core.services import access, field_leaves

    block = access.block_for(user, model_name)
    if block is None:
        return []                       # no block at all is handled by the caller
    allowed = set(block.get("edit") or [])
    if not allowed:
        return []                       # nothing editable is also the caller's business
    accepted = frozenset(field_leaves.collections(model_name))
    offered = {f"{prefix}{p}"
               for p in _leaf_paths(payload, collections=accepted) - _NOT_A_FIELD}
    return sorted(p for p in offered
                  if p not in allowed
                  and p.rsplit(".", 1)[-1] not in _NOT_A_FIELD
                  and p.split(".")[0] not in _NOT_A_FIELD)


def _transaction_save_denial(request, model_key: str, record_data: dict, lines_data: list):
    """Enforce role create/edit permission on /wcapi/transaction/save/.

    Returns (http_status, message) when denied, else None.
    For portal customers creating an order/quote, rewrites the payload in place:
    customer_id = their org, contact_id = themselves, status = planned, and every
    line re-priced server-side (client price/cost fields are discarded).
    """
    from apps.core.services import access
    from apps.core.services.role_filter import build_user_context, get_user_filter_config
    from apps.products.services.price_resolver import resolve_price_legacy

    user = request.user
    if not (user and user.is_authenticated):
        return status.HTTP_401_UNAUTHORIZED, "Authentication required"

    config = get_user_filter_config(user, model_key)
    if not config:
        return status.HTTP_403_FORBIDDEN, f"No permission for {model_key}"

    record_id = record_data.get("id")
    if not record_id:
        if not can_create(user, model_key):
            return status.HTTP_403_FORBIDDEN, f"Not permitted to create {model_key}"
    else:
        HeaderModel = registry.resolve(model_key)
        visible = HeaderModel is not None and HeaderModel.objects.filter(
            inject_role_filters(user, model_key)
        ).filter(pk=record_id).exists()
        if not visible or not config.get("edit"):
            return status.HTTP_403_FORBIDDEN, f"Not permitted to edit this {model_key}"

    # Size before shape. An enumeration governs which fields a payload may carry and can
    # say nothing about how many rows it carries, so the cap is checked first — before
    # anything is walked, re-priced or saved (Bill, 2026-09-20: "To address malicious
    # behavior we can limit their size").
    # Both shapes: /wcapi/save/ carries the collection inside the record, and
    # /wcapi/transaction/save/ passes it beside the record as its own argument.
    oversize = (_collection_too_large(model_key, record_data)
                or _collection_too_large(model_key, {'lines': lines_data or []}))
    if oversize:
        return status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, oversize

    # Field-level enforcement. The checks above answer "may this role edit this model"
    # and "may they see this row" — both filters. Neither says which fields, so this
    # endpoint used to accept any header field once edit was true, while /wcapi/save/
    # allowed only what the enumeration named (Bite 1 finding, fixed 2026-09-20).
    denied = _not_enumerated(user, model_key, record_data)
    if denied:
        return (status.HTTP_403_FORBIDDEN,
                f"Not permitted to write on {model_key}: {', '.join(denied[:8])}"
                + (f" (+{len(denied) - 8} more)" if len(denied) > 8 else ""))
    # A line's permissions live on the header's block, prefixed "lines." — that is how
    # the Settings are written (sales holds 189 lines.* paths of its 469 on order).
    for line in (lines_data or []):
        denied = _not_enumerated(user, model_key, line, prefix="lines.")
        if denied:
            return (status.HTTP_403_FORBIDDEN,
                    f"Not permitted to write on {model_key} lines: {', '.join(denied[:8])}"
                    + (f" (+{len(denied) - 8} more)" if len(denied) > 8 else ""))

    context = build_user_context(user)
    if not access.is_portal(user) or record_id or model_key not in _PORTAL_ORDER_MODELS:
        return None

    customer_ids = (context.get("org_ids") or {}).get("customer") or []
    if not customer_ids:
        return status.HTTP_403_FORBIDDEN, "No customer account is linked to this login"
    customer_id = customer_ids[0]

    # The portal role's own enumeration decides what survives — not a tuple in a view.
    from apps.core.services import access as _access
    portal_block = _access.block_for(user, model_key) or {}
    portal_allowed = {p.split(".")[0] for p in (portal_block.get("edit") or [])}
    safe_header = {k: v for k, v in record_data.items() if k in portal_allowed}
    record_data.clear()
    record_data.update(safe_header, customer_id=customer_id, contact_id=user.pk, status="planned")

    from apps.products.models import Item
    priced_lines = []
    for line in lines_data:
        item_env = line.get("item") if isinstance(line.get("item"), dict) else {}
        item_id = item_env.get("item_id") or item_env.get("id") or line.get("item_id")
        qty_env = line.get("quantity")
        qty = qty_env.get("active") if isinstance(qty_env, dict) else qty_env
        try:
            item_id, qty = int(item_id), int(qty)
        except (TypeError, ValueError):
            return status.HTTP_400_BAD_REQUEST, "Each line needs a numeric item_id and quantity"
        if qty <= 0:
            return status.HTTP_400_BAD_REQUEST, "Line quantity must be positive"
        item = Item.objects.filter(pk=item_id, is_active=True).first()
        if item is None:
            return status.HTTP_400_BAD_REQUEST, f"Item {item_id} is not available"
        quote = resolve_price_legacy(item_id, customer_id=customer_id, qty=qty)
        priced_lines.append({
            "_dirty": True,
            "item": {"item_id": item.pk, "ida_item": item.ida, "description": getattr(item, "name", "") or ""},
            "quantity": {"active": qty},
            "price": {"unit": quote["unit_price"]},
        })
    if not priced_lines:
        return status.HTTP_400_BAD_REQUEST, "Order has no lines"
    lines_data[:] = priced_lines
    return None


class WCAPITransactionSaveView(APIView):
    """Save transaction with lines, dirty tracking, and calculation verification.
    
    Lines are provided in `record.lines` (consistent with existing /wcapi/save/ pattern).
    
    Payload:
    {
        "model_name": "invoice",
        "record": {
            "id": 123,
            "totals": {...},
            "finance": {...},
            "lines": [                          // <-- Lines are INSIDE record
                { "id": 1, "_dirty": false, ... },  // Skipped - not dirty
                { "id": 2, "_dirty": true, ... },   // Updated - dirty
                { "_dirty": true, ... }             // Created - new line
            ]
        },
        "options": {
            "verify_calculations": true,  // Default: true
            "save_only_dirty": true        // Default: true
        }
    }
    
    Response:
    {
        "header": { "id": 123 },
        "lines": [
            { "id": 1, "action": "skipped", "reason": "not_dirty" },
            { "id": 2, "action": "updated" },
            { "id": 456, "action": "created" }
        ],
        "lines_saved": 2,
        "lines_skipped": 1,
        "action": "updated",
        "recalculated_totals": { ... }  // WC3's authoritative totals
    }
    """
    http_method_names = ["post", "options", "head"]

    def post(self, request, *args, **kwargs):
        from apps.transactions.services.transaction_save import (
            save_transaction_with_lines,
            CalculationMismatchError,
            ItemIdChangeError,
            TransferQuantityError,
            InsufficientInventoryError,
        )
        from common.write_through import is_write_through, forward_transaction_and_store
        
        body: Dict[str, Any] = request.data or {}
        model_key = body.get("model_name") or body.get("model") or body.get("modelName")
        record_data = body.get("record") or {}
        options = body.get("options") or {}
        
        # Extract lines from record.lines (consistent with /wcapi/save/ pattern)
        lines_data = record_data.pop("lines", []) or []
        
        if not model_key:
            return Response(
                {"detail": "model_name is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if model_key.lower() not in TRANSACTION_MODELS_WITH_LINES:
            return Response(
                {"detail": f"Model {model_key} does not support lines"},
                status=status.HTTP_400_BAD_REQUEST
            )

        denial = _transaction_save_denial(request, model_key.lower(), record_data, lines_data)
        if denial:
            logging.getLogger(__name__).warning(
                "Transaction save denied for %s user=%s: %s",
                model_key, getattr(request.user, "id", None), denial[1])
            return Response({"detail": denial[1]}, status=denial[0])

        # ── Write-through: forward to remote, store result locally ───
        if is_write_through():
            result, status_code = forward_transaction_and_store(
                request=request,
                model_key=model_key,
                record_data=record_data,
                lines_data=lines_data,
                options=options,
            )
            return Response(result, status=status_code)
        
        try:
            result = save_transaction_with_lines(
                model_key=model_key.lower(),
                header_data=record_data,
                lines_data=lines_data,
                request=request,
                verify_calculations=options.get("verify_calculations", True),
                save_only_dirty=options.get("save_only_dirty", True),
            )
            
            # Re-fetch the full saved record so the frontend gets a complete
            # Transaction object (with all fields & nested lines).
            # Post-save signal runs the real totals engine; re-fetched record
            # has authoritative totals (PJPV: one compute engine, read from JSON).
            saved_id = result.get('header', {}).get('id')
            if saved_id is not None:
                try:
                    from apps.core.services.record_serialize import get_item
                    saved_obj = get_item(model_key.lower(), request=request, id=saved_id)
                    if saved_obj is not None:
                        record_dict = to_dict(saved_obj)
                        # Attach lines
                        line_model_key = f"{model_key.lower()}line"
                        from apps.core.utils import registry
                        LineModel = registry.resolve(line_model_key)
                        if LineModel is not None:
                            from apps.transactions.services.transaction_save import _resolve_parent_fk
                            parent_fk = _resolve_parent_fk(LineModel, type(saved_obj), model_key.lower())
                            line_qs = LineModel.objects.filter(**{parent_fk: saved_id}).order_by('id')
                            record_dict['lines'] = [to_dict(ln) for ln in line_qs]
                        result['record'] = record_dict
                        # Authoritative totals from the saved record (PJPV: JSON envelope is source of truth)
                        totals_env = record_dict.get('totals')
                        if isinstance(totals_env, dict):
                            result['recalculated_totals'] = totals_env
                except Exception as fetch_err:
                    logger.warning("Failed to re-fetch saved record %s: %s", saved_id, fetch_err)

            # ── Local-sync: queue async push to remote DB ────────────
            if saved_id is not None:
                from common.sync_tasks import dispatch_sync_to_remote
                sync_task_id = dispatch_sync_to_remote(model_key.lower(), saved_id)  # record_id
                if sync_task_id:
                    result['sync_task_id'] = sync_task_id
                    result['sync_status'] = 'queued'

            return Response(result, status=status.HTTP_200_OK)
            
        except CalculationMismatchError as e:
            return Response({
                "detail": "Calculation mismatch",
                "error": str(e),
                "field": e.field,
                "r25_value": e.r25_value,
                "wc3_value": e.wc3_value,
                "line_id": e.line_id,
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except ItemIdChangeError as e:
            return Response({
                "detail": "Item ID change not allowed",
                "error": str(e),
                "line_id": e.line_id,
                "old_item_id": e.old_item_id,
                "new_item_id": e.new_item_id,
            }, status=status.HTTP_400_BAD_REQUEST)

        except TransferQuantityError as e:
            return Response({
                "detail": "Transfer quantity exceeds source remaining",
                "error": str(e),
                "source_model": e.source_model,
                "source_line_id": e.source_line_id,
                "requested": e.requested,
                "remaining": e.remaining,
            }, status=status.HTTP_400_BAD_REQUEST)

        except InsufficientInventoryError as e:
            return Response({
                "detail": "Insufficient inventory",
                "error": str(e),
                "item_id": e.item_id,
                "sku": e.sku,
                "required": e.required,
                "available": e.available,
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except LookupError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_404_NOT_FOUND
            )

        except IntegrityError as e:
            logger = logging.getLogger(__name__)
            logger.warning("Transaction save integrity error: %s", e)
            return Response({
                "detail": "Integrity error",
                "error": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.exception("Transaction save failed")
            import traceback
            return Response({
                "detail": "Save failed",
                "error": str(e),
                "traceback": traceback.format_exc()[-500:],
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class WCAPIGetView(APIView):
    http_method_names = ["post", "options", "head"]

    def post(self, request, *args, **kwargs):
        body: Dict[str, Any] = request.data or {}
        model_key = body.get("model_name") or body.get("model") or body.get("modelName")
        record_id = body.get("id")
        filters = body.get("filters") or {}
        fields: Optional[List[str]] = body.get("fields")

        ModelCls = registry.resolve(model_key or "")
        if not ModelCls:
            return Response({"detail": "invalid model"}, status=status.HTTP_400_BAD_REQUEST)

        qs: QuerySet = ModelCls.objects.active()
        qs = inject_constraints(qs, request, str(model_key))

        # Apply role-based access filters (RBAC)
        if request.user and request.user.is_authenticated:
            role_q = inject_role_filters(request.user, model_key)
            if role_q:
                qs = qs.filter(role_q)

        if record_id is not None:
            try:
                obj = qs.get(pk=record_id)
            except ModelCls.DoesNotExist:  # type: ignore[attr-defined]
                return Response({"item": None}, status=status.HTTP_200_OK)
            logger = logging.getLogger(__name__)
            try:
                logger.debug("WCAPIGetView: returning item id=%s refs_keys=%s", getattr(obj, 'pk', None), list((getattr(obj, 'refs', {}) or {}).get('links', {}).keys()))
            except Exception:
                pass
            data = to_dict(obj)
            try:
                from common.refs.contact_refs import normalize_refs_for_response
                data["refs"] = normalize_refs_for_response(data.get("refs"))
            except Exception:
                pass
            if fields:
                data = {k: data.get(k) for k in fields}
            model_name = getattr(getattr(ModelCls, "_meta", None), "model_name", "").lower()
            if model_name in TRANSACTION_MODELS_WITH_LINES:
                try:
                    related_manager = getattr(obj, "lines", None)
                    if hasattr(related_manager, "all"):
                        line_qs = related_manager.all()
                        try:
                            line_qs = line_qs.order_by("id")
                        except Exception:
                            pass
                        data["lines"] = [to_dict(line_obj) for line_obj in line_qs]
                    else:
                        data["lines"] = []
                except Exception:
                    data["lines"] = []
            return Response({"item": data}, status=status.HTTP_200_OK)

        if isinstance(filters, dict) and filters:
            qs = qs.filter(**filters)

        items: List[Dict[str, Any]] = []
        for obj in qs[:500]:
            logger = logging.getLogger(__name__)
            try:
                logger.debug("WCAPIGetView: list item id=%s refs_links_preview=%s", getattr(obj, 'pk', None), (getattr(obj, 'refs', {}) or {}).get('links'))
            except Exception:
                pass
            data = to_dict(obj)
            try:
                from common.refs.contact_refs import normalize_refs_for_response
                data["refs"] = normalize_refs_for_response(data.get("refs"))
            except Exception:
                pass
            if fields:
                data = {k: data.get(k) for k in fields}
            items.append(data)
        return Response({"items": items}, status=status.HTTP_200_OK)

class WCAPIQueryView(WCAPIGetView):
    def post(self, request, *args, **kwargs):
        body = dict(request.data or {})
        body.pop("id", None)  # force list
        request._full_data = body  # type: ignore[attr-defined]
        return super().post(request, *args, **kwargs)

class WCAPISaveView(APIView):
    http_method_names = ["post", "options", "head"]

    def post(self, request, *args, **kwargs):
        from common.write_through import is_write_through, forward_and_store

        body: Dict[str, Any] = request.data or {}
        model_key = body.get("model_name") or body.get("model") or body.get("modelName")
        record_id = body.get("id")
        data = body.get("data") or {}

        logger.debug(
            "WCAPISaveView: model_key=%s record_id=%s data_keys=%s",
            model_key, record_id,
            list(data.keys()) if isinstance(data, dict) else None,
        )

        ModelCls = registry.resolve(model_key or "")
        if not ModelCls or not isinstance(data, dict):
            return Response({"detail": "invalid payload"}, status=status.HTTP_400_BAD_REQUEST)

        # RBAC: Check create/edit permissions
        if request.user and request.user.is_authenticated and not request.user.is_superuser:
            is_create = record_id is None
            
            if is_create:
                # Check create permission
                if not can_create(request.user, model_key):
                    return Response(
                        {"detail": "Permission denied: cannot create records"},
                        status=status.HTTP_403_FORBIDDEN
                    )
            else:
                # For updates, get original data and validate fields
                try:
                    existing = ModelCls.objects.get(pk=record_id)
                    original_data = to_dict(existing)
                    is_valid, disallowed = validate_user_edit(
                        request.user, model_key, original_data, data
                    )
                    if not is_valid:
                        return Response(
                            {"detail": f"Permission denied: cannot edit fields: {', '.join(disallowed)}"},
                            status=status.HTTP_403_FORBIDDEN
                        )
                except ModelCls.DoesNotExist:
                    # Creating with explicit ID
                    if not can_create(request.user, model_key):
                        return Response(
                            {"detail": "Permission denied: cannot create records"},
                            status=status.HTTP_403_FORBIDDEN
                        )

        # ── Status guard: validate transitions and journalized locks ───
        GUARDED_MODELS = {
            'quote', 'order', 'invoice', 'purchase', 'workorder',
            'requisition', 'cash', 'invoice_line', 'purchase_line',
            'receipt_line',
        }
        if model_key in GUARDED_MODELS and record_id is not None:
            try:
                from apps.transactions.services.validate_status import (
                    validate_transition, validate_modification,
                )
                existing = ModelCls.objects.get(pk=record_id)

                # Check journalized lock — blocks all edits on posted records
                mod_result = validate_modification(existing, model_key)
                if not mod_result.can_proceed:
                    return Response(
                        {"detail": mod_result.errors[0], "errors": mod_result.errors},
                        status=status.HTTP_403_FORBIDDEN,
                    )

                # Check status transition if status is changing
                new_status = data.get('status')
                if new_status and new_status != getattr(existing, 'status', ''):
                    trans_result = validate_transition(existing, model_key, new_status)
                    if not trans_result.can_proceed:
                        return Response(
                            {"detail": trans_result.errors[0], "errors": trans_result.errors},
                            status=status.HTTP_400_BAD_REQUEST,
                        )
            except ModelCls.DoesNotExist:
                pass  # new record with explicit ID — no guard needed
            except Exception:
                pass  # guard failure should not block save

        # ── Write-through: forward to remote, store result locally ───
        if is_write_through():
            # Build a payload compatible with forward_and_store
            payload = dict(data)
            if record_id is not None:
                payload["id"] = record_id
            result, status_code = forward_and_store(request, ModelCls, payload)
            return Response(result, status=status_code)

        # Delegate to core save_item to centralize save behavior (including linking hooks)
        try:
            from apps.core.services.record_serialize import save_item as core_save_item
            obj_id, action, linked = core_save_item(model_key, request=request, data=data, id=record_id)
            status_code = status.HTTP_200_OK if action == "updated" else status.HTTP_201_CREATED
            return Response({"id": obj_id, "action": action, "linked": bool(linked)}, status=status_code)
        except LookupError:
            return Response({"detail": "not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.exception("Error saving via core save_item")
            return Response({"detail": "save failed", "error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class WCAPIDeleteView(APIView):
    http_method_names = ["post", "options", "head"]

    def post(self, request, *args, **kwargs):
        body: Dict[str, Any] = request.data or {}
        model_key = body.get("model_name")
        record_id = body.get("id")

        ModelCls = registry.resolve(model_key or "")
        if not ModelCls or record_id is None:
            return Response({"detail": "invalid payload"}, status=status.HTTP_400_BAD_REQUEST)

        # RBAC: Check delete permission
        if request.user and request.user.is_authenticated and not request.user.is_superuser:
            if not can_delete(request.user, model_key):
                return Response(
                    {"detail": "Permission denied: cannot delete records"},
                    status=status.HTTP_403_FORBIDDEN
                )

        try:
            obj = ModelCls.objects.get(pk=record_id)
        except ModelCls.DoesNotExist:  # type: ignore[attr-defined]
            return Response({"deleted": False, "id": record_id}, status=status.HTTP_200_OK)

        # Status guard: cannot delete journalized records
        if model_key in ('invoice', 'cash', 'purchase', 'invoice_line',
                         'purchase_line', 'receipt_line'):
            try:
                from apps.transactions.services.validate_status import is_journalized
                if is_journalized(obj):
                    return Response(
                        {"detail": f"Cannot delete — {model_key} has been journalized."},
                        status=status.HTTP_403_FORBIDDEN,
                    )
            except Exception:
                pass

        obj.delete()
        return Response({"deleted": True, "id": record_id}, status=status.HTTP_200_OK)

class WCAPISyncView(APIView):
    http_method_names = ["post", "options", "head"]

    def post(self, request, *args, **kwargs):
        """Handle data synchronization operations.
        
        Supports various sync operations:
        - bulk_create: Create multiple records
        - bulk_update: Update multiple records
        - upsert: Insert or update records based on unique constraints
        - sync_external: Sync data from external systems
        
        Expected payload format:
        {
            "operation": "bulk_create|bulk_update|upsert|sync_external",
            "model_name": "model_key",
            "data": [...],  # Array of records for bulk operations
            "sync_config": {...},  # Configuration for sync operations
            "conflict_resolution": "skip|overwrite|error"  # For upsert operations
        }
        """
        try:
            body: Dict[str, Any] = request.data or {}
            operation = body.get("operation")
            model_key = body.get("model_name") or body.get("model") or body.get("modelName")
            data = body.get("data", [])
            sync_config = body.get("sync_config", {})
            conflict_resolution = body.get("conflict_resolution", "skip")
            
            if not operation or not model_key:
                return Response({
                    "detail": "Missing required fields: operation, model_name"
                }, status=status.HTTP_400_BAD_REQUEST)
                
            # Resolve model
            ModelCls = registry.resolve(model_key)
            if not ModelCls:
                return Response({
                    "detail": f"Unknown model: {model_key}"
                }, status=status.HTTP_400_BAD_REQUEST)
                
            # Apply constraints to ensure user can access this model
            qs = ModelCls.objects.active()
            qs = inject_constraints(qs, request, str(model_key))
            
            # Route to appropriate sync operation
            if operation == "bulk_create":
                return self._bulk_create(ModelCls, data, qs)
            elif operation == "bulk_update":
                return self._bulk_update(ModelCls, data, qs)
            elif operation == "upsert":
                return self._upsert(ModelCls, data, conflict_resolution)
            elif operation == "sync_external":
                return self._sync_external(ModelCls, data, sync_config)
            else:
                return Response({
                    "detail": f"Unsupported operation: {operation}"
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Sync operation failed: {str(e)}", exc_info=True)
            return Response({
                "detail": "Sync operation failed",
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _bulk_create(self, ModelCls, data, qs):
        """Create multiple records in bulk."""
        if not isinstance(data, list):
            return Response({
                "detail": "Data must be an array for bulk_create operation"
            }, status=status.HTTP_400_BAD_REQUEST)
            
        created_records = []
        errors = []
        
        for i, record in enumerate(data):
            try:
                # Filter input fields to only include model fields
                clean_data = filter_input_fields(ModelCls, record)
                obj = ModelCls.objects.create(**clean_data)
                created_records.append({
                    "index": i,
                    "id": obj.pk,
                    "status": "created"
                })
            except Exception as e:
                errors.append({
                    "index": i,
                    "error": str(e),
                    "data": record
                })
                
        return Response({
            "operation": "bulk_create",
            "total_processed": len(data),
            "created": len(created_records),
            "errors": len(errors),
            "results": created_records,
            "error_details": errors
        }, status=status.HTTP_200_OK)
    
    def _bulk_update(self, ModelCls, data, qs):
        """Update multiple records in bulk."""
        if not isinstance(data, list):
            return Response({
                "detail": "Data must be an array for bulk_update operation"
            }, status=status.HTTP_400_BAD_REQUEST)
            
        updated_records = []
        errors = []
        
        for i, record in enumerate(data):
            try:
                record_id = record.get("id")
                if not record_id:
                    errors.append({
                        "index": i,
                        "error": "Missing 'id' field for bulk update",
                        "data": record
                    })
                    continue
                    
                # Filter input fields
                clean_data = filter_input_fields(ModelCls, record)
                # Remove id from update data
                clean_data.pop("id", None)
                
                obj = ModelCls.objects.filter(pk=record_id).first()
                if not obj:
                    errors.append({
                        "index": i,
                        "error": f"Record with id {record_id} not found",
                        "data": record
                    })
                    continue
                    
                for field, value in clean_data.items():
                    setattr(obj, field, value)
                obj.save()
                
                updated_records.append({
                    "index": i,
                    "id": obj.pk,
                    "status": "updated"
                })
            except Exception as e:
                errors.append({
                    "index": i,
                    "error": str(e),
                    "data": record
                })
                
        return Response({
            "operation": "bulk_update",
            "total_processed": len(data),
            "updated": len(updated_records),
            "errors": len(errors),
            "results": updated_records,
            "error_details": errors
        }, status=status.HTTP_200_OK)
    
    def _upsert(self, ModelCls, data, conflict_resolution):
        """Insert or update records based on unique constraints."""
        if not isinstance(data, list):
            return Response({
                "detail": "Data must be an array for upsert operation"
            }, status=status.HTTP_400_BAD_REQUEST)
            
        # Determine unique fields for upsert (excluding auto fields)
        unique_fields = []
        for field in ModelCls._meta.get_fields():
            if field.unique and not field.primary_key:
                unique_fields.append(field.name)
                
        if not unique_fields:
            return Response({
                "detail": "No unique fields found for upsert operation"
            }, status=status.HTTP_400_BAD_REQUEST)
            
        upserted_records = []
        errors = []
        
        for i, record in enumerate(data):
            try:
                # Build lookup criteria from unique fields
                lookup = {}
                for field in unique_fields:
                    if field in record:
                        lookup[field] = record[field]
                    else:
                        errors.append({
                            "index": i,
                            "error": f"Missing unique field: {field}",
                            "data": record
                        })
                        continue
                        
                if len(lookup) != len(unique_fields):
                    continue
                    
                # Filter input fields
                clean_data = filter_input_fields(ModelCls, record)
                
                # Try to get existing record
                obj = ModelCls.objects.filter(**lookup).first()
                
                if obj:
                    if conflict_resolution == "skip":
                        upserted_records.append({
                            "index": i,
                            "id": obj.pk,
                            "status": "skipped",
                            "action": "exists"
                        })
                        continue
                    elif conflict_resolution == "overwrite":
                        for field, value in clean_data.items():
                            setattr(obj, field, value)
                        obj.save()
                        upserted_records.append({
                            "index": i,
                            "id": obj.pk,
                            "status": "updated",
                            "action": "overwrite"
                        })
                    else:  # error
                        errors.append({
                            "index": i,
                            "error": f"Record with unique constraints already exists",
                            "data": record
                        })
                        continue
                else:
                    obj = ModelCls.objects.create(**clean_data)
                    upserted_records.append({
                        "index": i,
                        "id": obj.pk,
                        "status": "created",
                        "action": "insert"
                    })
                    
            except Exception as e:
                errors.append({
                    "index": i,
                    "error": str(e),
                    "data": record
                })
                
        return Response({
            "operation": "upsert",
            "total_processed": len(data),
            "upserted": len(upserted_records),
            "errors": len(errors),
            "results": upserted_records,
            "error_details": errors
        }, status=status.HTTP_200_OK)
    
    def _sync_external(self, ModelCls, data, sync_config):
        """Sync data from external systems with transformation and validation."""
        if not isinstance(data, list):
            return Response({
                "detail": "Data must be an array for sync_external operation"
            }, status=status.HTTP_400_BAD_REQUEST)
            
        # Apply field mappings if specified
        field_mappings = sync_config.get("field_mappings", {})
        transformed_data = []
        
        for record in data:
            transformed_record = {}
            for external_field, internal_field in field_mappings.items():
                if external_field in record:
                    transformed_record[internal_field] = record[external_field]
            # Include unmapped fields as-is
            for field, value in record.items():
                if field not in field_mappings:
                    transformed_record[field] = value
            transformed_data.append(transformed_record)
            
        # Process transformed data using bulk operations
        return self._bulk_create(ModelCls, transformed_data, ModelCls.objects.active())