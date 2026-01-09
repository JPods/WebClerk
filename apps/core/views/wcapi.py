from __future__ import annotations
from typing import Any, Dict, List, Optional, Set
import logging

from django.db.models import Q
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer

from apps.core.services import wcapi as services
from apps.core.utils import policy
from apps.core.utils.registry import resolve, get as get_registry_config
from common.api_responses import api_response

try:  # pragma: no cover - optional dependency in some deployments
    from apps.core.utils.model_policies import model_policies as mp  # noqa: F401
except Exception:  # pragma: no cover - fallback if policies unavailable
    mp = None


WcapiResponseSerializer = inline_serializer(
    name="WcapiResponse",
    fields={
        "record": serializers.JSONField(required=False, help_text="Single record when id parameter is provided"),
        "results": serializers.ListField(required=False, child=serializers.JSONField(), help_text="List of records"),
        "count": serializers.IntegerField(required=False, help_text="Number of records returned in this response"),
        "total": serializers.IntegerField(required=False, help_text="Total number of records matching the query"),
        "limit": serializers.IntegerField(required=False, help_text="Requested limit"),
        "offset": serializers.IntegerField(required=False, help_text="Applied offset"),
        "detail": serializers.CharField(required=False, help_text="Error message if request failed"),
    },
)


class WCAPIGetView(APIView):
    """Read-only WCAPI endpoint supporting query-parameter access with filtering, pagination, and search."""

    http_method_names = ["get", "options", "head"]

    LINE_MODEL_KEYS = {"proposal", "salesorder", "invoice", "purchaseorder", "workorder"}
    LINE_MODEL_MAP = {
        "proposal": "proposal_line",
        "salesorder": "sales_order_line",
        "invoice": "invoice_line",
        "purchaseorder": "purchase_order_line",
        "workorder": "work_order_line",
    }

    @staticmethod
    def _normalize_model_key(model_key: str | None) -> str:
        return (model_key or "").replace("/", "").replace("_", "").lower()

    def _should_include_lines(self, model_key: str | None) -> bool:
        return self._normalize_model_key(model_key) in self.LINE_MODEL_KEYS

    def _serialize_lines(self, obj, request) -> List[Dict[str, Any]]:
        manager = getattr(obj, "lines", None)
        if not hasattr(manager, "all"):
            return []
        try:
            qs = manager.all()
            try:
                qs = qs.order_by("id")
            except Exception:
                pass
        except Exception:
            return []

        results: List[Dict[str, Any]] = []
        for line in qs:
            try:
                allow = policy.field_allowlist(type(line), request=request)
                payload = services.to_dict(line, allow=allow)
            except Exception:
                payload = {}
            if not isinstance(payload, dict):
                continue
            if payload.get("is_deleted") is True:
                continue
            results.append(payload)
        return results

    def _line_model_key(self, model_key: str | None) -> Optional[str]:
        if not model_key:
            return None
        return self.LINE_MODEL_MAP.get(self._normalize_model_key(model_key))

    def _merge_line_dicts(self, primary: Dict[str, Any], secondary: Dict[str, Any]) -> Dict[str, Any]:
        merged = dict(primary or {})
        for key, value in (secondary or {}).items():
            if key not in merged or merged[key] in (None, "", [], {}):
                merged[key] = value
        return merged

    def _extract_lines_from_refs(self, obj, model_key: str, request) -> List[Dict[str, Any]]:
        try:
            refs = getattr(obj, "refs", {}) or {}
        except Exception:
            return []

        if not isinstance(refs, dict):
            return []

        links = refs.get("links")
        if not isinstance(links, dict):
            return []

        line_model_key = self._line_model_key(model_key)
        if not line_model_key:
            return []

        target_norm = self._normalize_model_key(line_model_key).rstrip('s')
        raw_entries: List[Any] = []
        for key, bucket in links.items():
            key_norm = self._normalize_model_key(str(key)).rstrip('s')
            if key_norm != target_norm:
                continue
            if isinstance(bucket, list):
                raw_entries.extend(bucket)

        if not raw_entries:
            return []

        fetch_ids: Set[int] = set()
        for entry in raw_entries:
            if isinstance(entry, dict):
                ident = entry.get("id")
            else:
                ident = entry
            if isinstance(ident, int):
                fetch_ids.add(ident)
            elif isinstance(ident, str) and ident.isdigit():
                fetch_ids.add(int(ident))

        fetched_map: Dict[int, Dict[str, Any]] = {}
        if fetch_ids and line_model_key:
            try:
                ModelCls, qs = services.get_queryset(line_model_key, request=request)
                objs = list(qs.filter(pk__in=fetch_ids))
                for line in objs:
                    allow_line = policy.field_allowlist(type(line), request=request)
                    fetched_map[getattr(line, "pk")] = services.to_dict(line, allow=allow_line)
            except Exception:
                pass

        entries: List[Dict[str, Any]] = []
        for entry in raw_entries:
            if isinstance(entry, dict):
                data = dict(entry)
                ident = data.get("id")
                parsed_id = None
                if isinstance(ident, int):
                    parsed_id = ident
                elif isinstance(ident, str) and ident.isdigit():
                    parsed_id = int(ident)
                    data["id"] = parsed_id
                if parsed_id is not None and parsed_id in fetched_map:
                    data = self._merge_line_dicts(fetched_map[parsed_id], data)
                entries.append(data)
            else:
                parsed_id = None
                if isinstance(entry, int):
                    parsed_id = entry
                elif isinstance(entry, str) and entry.isdigit():
                    parsed_id = int(entry)
                if parsed_id is not None and parsed_id in fetched_map:
                    entries.append(fetched_map[parsed_id])
                elif parsed_id is not None:
                    entries.append({"id": parsed_id})

        return entries

    def _merge_line_records(self, primary: List[Dict[str, Any]], supplements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not primary:
            return [dict(item) for item in supplements if isinstance(item, dict)]
        merged: List[Dict[str, Any]] = [dict(item) for item in primary if isinstance(item, dict)]
        index: Dict[int, int] = {}
        for idx, item in enumerate(merged):
            ident = item.get("id")
            if isinstance(ident, int):
                index[ident] = idx
        for sup in supplements:
            if not isinstance(sup, dict):
                continue
            data = dict(sup)
            ident = data.get("id")
            if isinstance(ident, str) and ident.isdigit():
                ident = int(ident)
                data["id"] = ident
            if isinstance(ident, int) and ident in index:
                merged[index[ident]] = self._merge_line_dicts(merged[index[ident]], data)
            else:
                merged.append(data)
                if isinstance(ident, int):
                    index[ident] = len(merged) - 1
        return merged

    def _collect_lines(self, obj, model_key: str, request) -> List[Dict[str, Any]]:
        db_lines = self._serialize_lines(obj, request)
        ref_lines = self._extract_lines_from_refs(obj, model_key, request)
        if not db_lines:
            return ref_lines
        if not ref_lines:
            return db_lines
        return self._merge_line_records(db_lines, ref_lines)

    def _parse_filters(self, request, model_key: str, ModelCls) -> Dict[str, Any]:
        """
        Parse and validate filter parameters from query string.
        
        Supports:
        - Field equality: ?status=active&priority=high
        - Field comparisons: ?created_after=2025-01-01&amount__gte=100
        - Negation: ?status__ne=canceled
        
        Returns dict of filters safe to apply to queryset.
        """
        filters = {}
        field_names = {f.name for f in ModelCls._meta.get_fields()}
        
        for key, value in request.query_params.items():
            # Skip reserved parameters
            if key in {'model_name', 'id', 'fields', 'limit', 'offset', 'page', 'page_size', 
                      'q', 'search', 'order_by', 'ordering', 'model_name_filter'}:
                continue
            
            # Validate field name (before __lookup)
            field_base = key.split('__')[0]
            if field_base not in field_names:
                continue
            
            # Support common lookup formats
            if '__' in key:
                lookup_type = key.split('__')[1]
                # Support common lookups: gte, lte, gt, lt, in, startswith, endswith, icontains
                allowed_lookups = {
                    'gte', 'lte', 'gt', 'lt', 'in', 'startswith', 'endswith', 'icontains',
                    'exact', 'iexact', 'contains', 'range', 'isnull', 'ne'
                }
                if lookup_type not in allowed_lookups:
                    continue
                
                # Handle 'ne' (not equal) by converting to Q object later
                if lookup_type == 'ne':
                    # Store for later Q object handling
                    filters[key] = value
                    continue
            
            filters[key] = value
        
        return filters

    def _parse_search(self, request, model_key: str, ModelCls) -> Optional[str]:
        """
        Get search query from 'q' or 'search' parameter.
        
        Returns search string or None if not provided.
        """
        search_query = (request.query_params.get('q') or request.query_params.get('search') or '').strip()
        return search_query if search_query else None

    def _apply_search(self, qs, search_query: str, model_key: str, ModelCls) -> Any:
        """
        Apply full-text search across configured search fields.
        
        Uses registry config to determine which fields are searchable.
        Falls back to common fields if not configured.
        """
        if not search_query:
            return qs
        
        # Get search fields from registry config
        config = get_registry_config(model_key)
        search_fields = list(config.search_fields) if config and config.search_fields else []
        
        # Fallback to common searchable fields
        if not search_fields:
            fallback_fields = []
            for f in ModelCls._meta.get_fields():
                if hasattr(f, 'get_internal_type'):
                    ftype = f.get_internal_type()
                    # Include text-based and common fields
                    if ftype in {'CharField', 'TextField', 'EmailField', 'URLField', 'SlugField'}:
                        fallback_fields.append(f.name)
                    # Include common identifier fields
                    elif f.name in {'name', 'title', 'email', 'code', 'reference', 'description'}:
                        fallback_fields.append(f.name)
            search_fields = fallback_fields[:10]  # Limit to 10 fields
        
        if not search_fields:
            return qs
        
        # Build search condition with OR
        search_condition = Q()
        for field in search_fields:
            search_condition |= Q(**{f"{field}__icontains": search_query})
        
        try:
            return qs.filter(search_condition)
        except Exception:
            # If search fails, return unfiltered queryset
            return qs

    def _apply_filters(self, qs, filters: Dict[str, Any]) -> Any:
        """
        Apply validated filters to queryset with proper Q object handling.
        
        Handles both regular filters and 'ne' (not equal) filters.
        """
        if not filters:
            return qs
        
        # Separate 'ne' filters (not equal)
        ne_filters = {}
        regular_filters = {}
        
        for key, value in filters.items():
            if '__ne' in key:
                ne_filters[key.replace('__ne', '')] = value
            else:
                regular_filters[key] = value
        
        try:
            # Apply regular filters
            if regular_filters:
                qs = qs.filter(**regular_filters)
            
            # Apply not-equal filters using Q object negation
            for key, value in ne_filters.items():
                qs = qs.exclude(**{key: value})
        except Exception:
            # If filtering fails, return the queryset as-is
            pass
        
        return qs

    def _parse_pagination(self, request) -> tuple[int, int]:
        """
        Parse pagination parameters (limit/offset or page/page_size).
        
        Returns (limit, offset) tuple.
        
        Supports:
        - limit + offset: ?limit=50&offset=100
        - page + page_size: ?page=2&page_size=50 (page is 1-indexed)
        """
        # Check for page-based pagination first
        page = request.query_params.get('page')
        page_size = request.query_params.get('page_size')
        
        if page and page_size:
            try:
                page_num = max(1, int(page))
                size = min(int(page_size), 1000)  # Max 1000 per page
                size = max(1, size)
                offset = (page_num - 1) * size
                return size, offset
            except (ValueError, TypeError):
                pass
        
        # Fall back to limit + offset
        limit = request.query_params.get('limit', '500')
        offset = request.query_params.get('offset', '0')
        
        try:
            limit_int = min(int(limit), 1000)  # Max 1000 records
            limit_int = max(1, limit_int)
            offset_int = max(0, int(offset))
            return limit_int, offset_int
        except (ValueError, TypeError):
            return 500, 0

    def _parse_ordering(self, request, model_key: str, ModelCls) -> Optional[str]:
        """
        Parse and validate ordering parameter.
        
        Supports: ?ordering=field_name or ?ordering=-field_name or ?order_by=...
        
        Returns validated ordering string or None.
        """
        ordering = request.query_params.get('ordering') or request.query_params.get('order_by')
        if not ordering:
            return None
        
        # Map common field names
        ordering_map = {
            'created_at': 'dt_created',
            '-created_at': '-dt_created',
            'updated_at': 'dt_modified',
            '-updated_at': '-dt_modified',
            'name': 'name',
            '-name': '-name',
        }
        
        if ordering in ordering_map:
            ordering = ordering_map[ordering]
        
        # Validate field exists (remove - prefix if present)
        field_name = ordering.lstrip('-')
        field_names = {f.name for f in ModelCls._meta.get_fields()}
        
        if field_name not in field_names:
            return None
        
        try:
            # Test ordering by applying to empty queryset
            ModelCls.objects.all().order_by(ordering)
            return ordering
        except Exception:
            return None

    def _handle(
        self,
        model_key: str,
        record_id: Optional[Any],
        fields: Optional[List[str]],
        request,
    ) -> Response:
        """Main handler for GET requests with full filtering/search/pagination support."""
        
        if not resolve(model_key):
                return api_response(
                success=False,
                status_code=status.HTTP_400_BAD_REQUEST,
                message="invalid model",
                error={"code": "invalid_model", "details": model_key},
            )

        # Single record retrieval
        if record_id is not None:
            obj = services.get_item(model_key, request=request, id=record_id)
            if not obj:
                return api_response(data={"record": None}, status_code=status.HTTP_200_OK)

            allow = policy.field_allowlist(type(obj), request=request)
            logger = logging.getLogger(__name__)
            field_names: Set[str] = set()
            try:
                refs = getattr(obj, 'refs', {}) or {}
                email_bucket = refs.get('links', {}).get('email') if isinstance(refs.get('links', {}), dict) else None
                if email_bucket:
                    logger.info("WCAPIGetView: id=%s has %d denorm email links", getattr(obj, 'pk', None), len(email_bucket))
                try:
                    from apps.core.models import Contact as _Contact
                    db_refs = _Contact.objects.filter(pk=getattr(obj, 'pk', None)).values_list('refs', flat=True).first()
                    if isinstance(db_refs, dict) and db_refs.get('links', {}).get('email'):
                        logger.info("WCAPIGetView: id=%s DB has %d denorm email links", getattr(obj, 'pk', None), len(db_refs.get('links', {}).get('email')))
                except Exception:
                    pass
            except Exception:
                pass

            try:
                field_names = {f.name for f in obj._meta.get_fields()}
            except Exception:
                field_names = set()

            payload = services.to_dict(obj, allow=allow)
            if self._should_include_lines(model_key):
                payload["lines"] = self._collect_lines(obj, model_key, request)
                if "results" in payload and "results" not in field_names and isinstance(payload["results"], list):
                    payload.pop("results", None)
            else:
                if "results" in payload and "results" not in field_names and isinstance(payload["results"], list):
                    payload.pop("results", None)
            return api_response(data={"record": payload}, status_code=status.HTTP_200_OK)

        # List retrieval with filters, search, and pagination
        ModelCls, qs = services.get_queryset(model_key, request=request)
        
        # Apply search first (before filters for better performance with indexes)
        search_query = self._parse_search(request, model_key, ModelCls)
        if search_query:
            qs = self._apply_search(qs, search_query, model_key, ModelCls)
        
        # Parse and apply filters
        filters = self._parse_filters(request, model_key, ModelCls)
        qs = self._apply_filters(qs, filters)
        
        # Get total count before pagination
        total_count = qs.count()
        
        # Parse and apply ordering
        ordering = self._parse_ordering(request, model_key, ModelCls)
        if ordering:
            qs = qs.order_by(ordering)
        else:
            # Default ordering
            try:
                qs = qs.order_by('-dt_created')
            except Exception:
                try:
                    qs = qs.order_by('-id')
                except Exception:
                    pass
        
        # Parse pagination
        limit, offset = self._parse_pagination(request)
        
        # Apply pagination
        qs_paginated = qs[offset:offset + limit]
        items = list(qs_paginated)
        
        # Serialize results
        allow = policy.field_allowlist(ModelCls, request=request) if ModelCls else None
        results = [services.to_dict(o, allow=allow) for o in items]
        
        # Build response with pagination metadata
        page_number = (offset // limit) + 1 if limit > 0 else 1
        total_pages = (total_count + limit - 1) // limit if limit > 0 else 1
        
        response_data = {
            "results": results,
            "count": len(results),
            "total": total_count,
            "limit": limit,
            "offset": offset,
            "page": page_number,
            "total_pages": total_pages,
            "has_next": offset + limit < total_count,
            "has_previous": offset > 0,
        }
        
        # Include query parameters echo for debugging
        if request.query_params:
            response_data["query"] = {
                "search": search_query,
                "filters": filters,
                "ordering": ordering,
                "pagination": {"limit": limit, "offset": offset}
            }
        
        return api_response(data=response_data, status_code=status.HTTP_200_OK)

    @extend_schema(
        operation_id="wcapi_get_list_query",
        summary="Get records with filtering, search, and pagination",
        description="""
Retrieve records from any configured model with comprehensive query support.

**Filtering:** Use field parameters for equality or lookups
  - Equality: ?status=active&priority=high
  - Comparisons: ?created_after=2025-01-01&amount__gte=100
  - Lookups: __gte, __lte, __gt, __lt, __icontains, __startswith, __endswith
  - Negation: ?status__ne=canceled

**Search:** Full-text search across configured searchable fields
  - ?q=search_term or ?search=search_term
  - Uses model's configured search_fields from registry
  - Falls back to common fields (name, title, email, code, etc.)

**Pagination:** Support both limit/offset and page-based pagination
  - Limit/offset: ?limit=50&offset=100
  - Page-based: ?page=2&page_size=25 (1-indexed)
  - Default: limit=500, max=1000

**Ordering:** Sort results by field
  - ?ordering=field_name or ?order_by=-field_name
  - Maps: created_at→dt_created, updated_at→dt_modified
  - Supports descending with - prefix

**Combined Example:**
  GET /api/wcapi/get/?model_name=invoice&status=sent&q=customer_name&page=1&page_size=25&ordering=-dt_created
        """,
        parameters=[
            OpenApiParameter(
                name="model_name",
                type=str,
                required=True,
                location=OpenApiParameter.QUERY,
                description="Model key from WCAPI registry (e.g., 'contact', 'invoice', 'salesorder')",
                examples=["proposal", "salesorder", "invoice", "contact"],
            ),
            OpenApiParameter(
                name="id",
                type=int,
                required=False,
                location=OpenApiParameter.QUERY,
                description="Specific record ID to retrieve (returns single item instead of list)",
            ),
            OpenApiParameter(
                name="fields",
                type=str,
                required=False,
                location=OpenApiParameter.QUERY,
                description="Comma-separated list of fields to include in response",
            ),
            OpenApiParameter(
                name="q",
                type=str,
                required=False,
                location=OpenApiParameter.QUERY,
                description="Search query - searches across model's searchable fields (case-insensitive)",
            ),
            OpenApiParameter(
                name="limit",
                type=int,
                required=False,
                location=OpenApiParameter.QUERY,
                description="Maximum number of records to return (default: 500, max: 1000)",
            ),
            OpenApiParameter(
                name="offset",
                type=int,
                required=False,
                location=OpenApiParameter.QUERY,
                description="Number of records to skip for pagination (use with limit)",
            ),
            OpenApiParameter(
                name="page",
                type=int,
                required=False,
                location=OpenApiParameter.QUERY,
                description="Page number (1-indexed) when using page-based pagination",
            ),
            OpenApiParameter(
                name="page_size",
                type=int,
                required=False,
                location=OpenApiParameter.QUERY,
                description="Records per page (use with page parameter)",
            ),
            OpenApiParameter(
                name="ordering",
                type=str,
                required=False,
                location=OpenApiParameter.QUERY,
                description="Field to order by (prefix with '-' for descending, e.g., '-dt_created')",
            ),
        ],
        responses={
            200: WcapiResponseSerializer,
            400: WcapiResponseSerializer,
            401: WcapiResponseSerializer,
        },
    )
    def get(self, request, **kwargs):
        model_key = request.query_params.get("model_name")
        if not model_key:
            return Response(
                {"detail": "model_name parameter is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        record_id = request.query_params.get("id")
        
        return self._handle(model_key, record_id, None, request)


class ModelNameListView(APIView):
    """List available model names."""

    http_method_names = ["get", "options", "head"]

    @extend_schema(
        operation_id="model_name_list",
        summary="Get list of model names",
        description="Retrieve list of available model names for the admin workbench.",
        responses={
            200: inline_serializer(
                name="ModelNameListResponse",
                fields={
                    "model_names": serializers.ListField(child=serializers.CharField()),
                    "count": serializers.IntegerField(),
                },
            ),
        },
    )
    def get(self, request, **kwargs):
        from django.apps import apps
        from apps.core.utils.registry import resolve
        models = apps.get_models()
        model_names = [model._meta.model_name for model in models if model._meta.model_name != "setting" and resolve(model._meta.model_name)]
        return Response({
            "status": "success",
            "code": 200,
            "message": "OK",
            "data": {"model_names": model_names, "count": len(model_names)}
        }, status=status.HTTP_200_OK)


class ModelDetailView(APIView):
    """Get model details including fields."""

    http_method_names = ["get", "options", "head"]

    @extend_schema(
        operation_id="model_detail",
        summary="Get model details",
        description="Retrieve model metadata including field definitions.",
        parameters=[
            OpenApiParameter(
                name="model_name",
                type=str,
                required=True,
                location=OpenApiParameter.QUERY,
                description="Model key to get details for",
            ),
        ],
        responses={
            200: inline_serializer(
                name="ModelDetailResponse",
                fields={
                    "model": inline_serializer(
                        name="ModelInfo",
                        fields={
                            "model_name": serializers.CharField(),
                            "fields": serializers.ListField(child=serializers.JSONField()),
                        },
                    ),
                },
            ),
            400: inline_serializer(
                name="ErrorResponse",
                fields={"detail": serializers.CharField()},
            ),
        },
    )
    def get(self, request, **kwargs):
        from apps.core.utils.registry import resolve
        model_key = request.query_params.get("model_name")
        if not model_key:
            return Response({"detail": "model_name required"}, status=status.HTTP_400_BAD_REQUEST)

        ModelCls = resolve(model_key)
        if not ModelCls:
            return Response({"detail": "invalid model"}, status=status.HTTP_400_BAD_REQUEST)

        fields = []
        for f in ModelCls._meta.fields:
            fields.append({"name": f.name, "type": f.__class__.__name__})

        return Response(
            {
                "status": "success",
                "code": 200,
                "message": "OK",
                "data": {
                    "model": {
                        "model_name": model_key,
                        "fields": fields,
                    }
                }
            },
            status=status.HTTP_200_OK,
        )
