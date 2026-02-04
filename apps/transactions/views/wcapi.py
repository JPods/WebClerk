from __future__ import annotations
from typing import Any, Dict, List, Optional
from django.forms.models import model_to_dict
import logging
from django.db.models import QuerySet, Model
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from apps.core.utils import registry

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
    model_fields = {f.name for f in getattr(ModelCls._meta, "fields", [])}
    return {k: v for k, v in (payload or {}).items() if k in model_fields}

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
    "proposal",
    "salesorder",
    "invoice",
    "purchaseorder",
    "workorder",
}


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
            calculate_header_totals,
            CalculationMismatchError,
            ItemIdChangeError,
        )
        
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
        
        try:
            result = save_transaction_with_lines(
                model_key=model_key.lower(),
                header_data=record_data,
                lines_data=lines_data,
                request=request,
                verify_calculations=options.get("verify_calculations", True),
                save_only_dirty=options.get("save_only_dirty", True),
            )
            
            # Calculate and return authoritative totals
            recalc_totals = calculate_header_totals(lines_data, record_data)
            result['recalculated_totals'] = {
                k: float(v) for k, v in recalc_totals.items()
            }
            
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
            
        except LookupError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
            
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.exception("Transaction save failed")
            return Response({
                "detail": "Save failed",
                "error": str(e)
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

        qs: QuerySet = ModelCls.objects.all()
        qs = inject_constraints(qs, request, str(model_key))

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
        body: Dict[str, Any] = request.data or {}
        model_key = body.get("model_name") or body.get("model") or body.get("modelName")
        record_id = body.get("id")
        data = body.get("data") or {}

        # DEBUG: Print to stdout to see in runserver terminal
        print(f"\n{'='*60}")
        print(f"WCAPISaveView DEBUG:")
        print(f"  model_key: {model_key}")
        print(f"  record_id: {record_id}")
        print(f"  data keys: {list(data.keys()) if isinstance(data, dict) else None}")
        print(f"  contact_id from data: {data.get('contact_id') if isinstance(data, dict) else None}")
        print(f"{'='*60}\n")

        ModelCls = registry.resolve(model_key or "")
        if not ModelCls or not isinstance(data, dict):
            return Response({"detail": "invalid payload"}, status=status.HTTP_400_BAD_REQUEST)

        # Delegate to core save_item to centralize save behavior (including linking hooks)
        try:
            from apps.core.services.wcapi import save_item as core_save_item
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

        try:
            obj = ModelCls.objects.get(pk=record_id)
        except ModelCls.DoesNotExist:  # type: ignore[attr-defined]
            return Response({"deleted": False, "id": record_id}, status=status.HTTP_200_OK)

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
            qs = ModelCls.objects.all()
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
        return self._bulk_create(ModelCls, transformed_data, ModelCls.objects.all())