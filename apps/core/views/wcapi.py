from __future__ import annotations
from typing import Any, Dict, List, Optional, Set
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

from django.db.models import Q
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from django.utils import timezone

from apps.core.services import wcapi as services
from apps.core.constants.filter_operators import ALLOWED_LOOKUPS
from apps.core.services.role_filter import inject_role_filters
from apps.core.services.field_projection import filter_response_data
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


class WCAPIDeleteView(APIView):
    """Delete WCAPI endpoint supporting record removal by model_name and id."""

    http_method_names = ["get", "post", "options", "head"]

    def get(self, request, *args, **kwargs):
        """Handle GET requests with query params: ?model_name=X&id=Y"""
        model_key = request.query_params.get("model_name") or request.query_params.get("model")
        record_id = request.query_params.get("id")
        return self._do_delete(request, model_key, record_id)

    def post(self, request, *args, **kwargs):
        """Handle POST requests with body: { model_name, id }"""
        body: Dict[str, Any] = request.data or {}
        model_key = body.get("model_name") or body.get("model") or body.get("modelName")
        record_id = body.get("id")
        return self._do_delete(request, model_key, record_id)

    def _do_delete(self, request, model_key, record_id):
        """Shared delete logic for GET and POST."""
        from django.conf import settings as _settings
        if getattr(_settings, 'READ_ONLY_MODE', False):
            return api_response(
                success=False, status_code=405,
                message='This is a read-only demo. Download WebClerk at webclerk.com to modify data.',
                error={'code': 'demo_read_only', 'details': 'Deletes are disabled on the demo instance.'})

        if not model_key or record_id is None:
            return api_response(
                success=False,
                status_code=status.HTTP_400_BAD_REQUEST,
                message="invalid payload",
                error={"code": "invalid_payload", "details": {"model_name": model_key, "id": record_id}},
            )

        try:
            deleted = services.delete_item(model_key, request=request, id=record_id)
        except Exception:
            return api_response(
                success=False,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="delete failed",
                error={"code": "delete_failed", "details": {"model_name": model_key, "id": record_id}},
            )

        return api_response(
            data={"deleted": bool(deleted), "id": record_id, "model_name": model_key},
            status_code=status.HTTP_200_OK,
        )


class WCAPIGetView(APIView):
    """Read-only WCAPI endpoint supporting query-parameter access with filtering, pagination, and search."""

    http_method_names = ["get", "options", "head"]

    LINE_MODEL_KEYS = {"proposal", "order", "invoice", "purchase", "workorder"}
    LINE_MODEL_MAP = {
        "proposal": "proposal_line",
        "order": "order_line",
        "invoice": "invoice_line",
        "purchase": "purchase_line",
        "workorder": "workorderline",
    }

    def _action_attachments_map(self, action_ids: List[int]) -> Dict[int, List[Dict[str, Any]]]:
        if not action_ids:
            return {}

        try:
            from apps.docs.models import Document, LinkageEntry
        except Exception:
            return {}

        action_entries = list(
            LinkageEntry.objects.filter(
                model_name="action",
                record_id__in=action_ids,
                purpose="attachment",
            ).values("record_id", "group_id")
        )
        if not action_entries:
            return {}

        group_to_actions: Dict[int, List[int]] = {}
        for row in action_entries:
            group_id = row.get("group_id")
            record_id = row.get("record_id")
            if not isinstance(group_id, int) or not isinstance(record_id, int):
                continue
            group_to_actions.setdefault(group_id, []).append(record_id)

        if not group_to_actions:
            return {}

        group_ids = list(group_to_actions.keys())
        doc_entries = list(
            LinkageEntry.objects.filter(
                model_name="document",
                group_id__in=group_ids,
                purpose="attachment",
            ).values("group_id", "record_id")
        )

        document_ids = {
            row.get("record_id")
            for row in doc_entries
            if isinstance(row.get("record_id"), int)
        }
        documents = {
            doc.id: doc
            for doc in Document.objects.filter(id__in=document_ids)
        }

        result: Dict[int, List[Dict[str, Any]]] = {action_id: [] for action_id in action_ids}
        for row in doc_entries:
            group_id = row.get("group_id")
            doc_id = row.get("record_id")
            if not isinstance(group_id, int) or not isinstance(doc_id, int):
                continue
            doc = documents.get(doc_id)
            if not doc:
                continue

            doc_path = doc.path if isinstance(doc.path, dict) else {}
            url = doc_path.get("url") or f"/wcapi/document/{doc.id}/"
            attachment_payload = {
                "id": doc.id,
                "name": doc.name,
                "mime_type": doc.mime_type,
                "size_bytes": doc.size_bytes,
                "url": url,
                "path": doc.path,
            }

            for action_id in group_to_actions.get(group_id, []):
                result.setdefault(action_id, []).append(attachment_payload)

        return result

    @staticmethod
    def _normalize_model_key(model_key: str | None) -> str:
        return (model_key or "").replace("/", "").replace("_", "").lower()

    def _should_include_lines(self, model_key: str | None) -> bool:
        return self._normalize_model_key(model_key) in self.LINE_MODEL_KEYS

    def _serialize_lines(self, obj, request) -> List[Dict[str, Any]]:
        logger.debug("_serialize_lines: obj.id=%s", getattr(obj, 'id', '?'))
        
        manager = getattr(obj, "lines", None)
        if not hasattr(manager, "all"):
            logger.debug("_serialize_lines: no lines manager, returning []")
            return []
        try:
            qs = manager.all()
            try:
                qs = qs.order_by("id")
            except Exception:
                pass
        except Exception as e:
            logger.error("_serialize_lines: exception getting queryset: %s", e)
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
                logger.debug("_serialize_lines: skipping deleted line id=%s", payload.get('id'))
                continue
            results.append(payload)
        logger.debug("_serialize_lines: returning %d lines", len(results))
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
        logger.debug("_collect_lines: model_key=%s obj.id=%s", model_key, getattr(obj, 'id', '?'))
        
        db_lines = self._serialize_lines(obj, request)
        ref_lines = self._extract_lines_from_refs(obj, model_key, request)
        
        if not db_lines:
            return ref_lines
        if not ref_lines:
            return db_lines
        merged = self._merge_line_records(db_lines, ref_lines)
        logger.debug("_collect_lines: merged %d db + %d ref → %d lines", len(db_lines), len(ref_lines), len(merged))
        return merged

    def _field_types(self, ModelCls) -> Dict[str, str]:
        field_types: Dict[str, str] = {}
        for field in ModelCls._meta.get_fields():
            if hasattr(field, "get_internal_type"):
                field_types[field.name] = field.get_internal_type()
        return field_types

    def _coerce_filter_value(self, field_type: str, value: Any, lookup_type: str = "exact") -> Any:
        if value is None:
            return None

        if lookup_type in {"in", "range"}:
            if isinstance(value, str):
                parts = [part.strip() for part in value.split(",") if part.strip()]
            elif isinstance(value, list):
                parts = value
            else:
                parts = [value]
            return [self._coerce_filter_value(field_type, part, "exact") for part in parts]

        if isinstance(value, str):
            lowered = value.lower()
            if field_type in {"BooleanField", "NullBooleanField"}:
                if lowered in {"true", "1", "yes"}:
                    return True
                if lowered in {"false", "0", "no"}:
                    return False
                if lowered in {"null", "none", ""}:
                    return None

            if field_type in {"IntegerField", "BigIntegerField", "PositiveIntegerField", "SmallIntegerField"}:
                try:
                    return int(value)
                except (TypeError, ValueError):
                    return value

            if field_type in {"FloatField", "DecimalField"}:
                try:
                    return float(value)
                except (TypeError, ValueError):
                    return value

        return value

    def _resolve_relative_period(self, spec: Any) -> Dict[str, int]:
        if not isinstance(spec, dict):
            return {}

        field_name = str(spec.get("field") or "").strip()
        preset = str(spec.get("preset") or "").strip().lower()
        if not field_name or not preset:
            return {}

        now = timezone.localtime(timezone.now())
        if preset == "current_month":
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if start.month == 12:
                next_start = start.replace(year=start.year + 1, month=1)
            else:
                next_start = start.replace(month=start.month + 1)
        elif preset == "current_quarter":
            quarter_start_month = ((now.month - 1) // 3) * 3 + 1
            start = now.replace(month=quarter_start_month, day=1, hour=0, minute=0, second=0, microsecond=0)
            if quarter_start_month == 10:
                next_start = start.replace(year=start.year + 1, month=1)
            else:
                next_start = start.replace(month=quarter_start_month + 3)
        else:
            return {}

        end = next_start - timedelta(milliseconds=1)
        return {
            f"{field_name}__gte": int(start.timestamp() * 1000),
            f"{field_name}__lte": int(end.timestamp() * 1000),
        }

    def _request_filter_specs(self, saved_data: Dict[str, Any], ModelCls) -> Dict[str, Dict[str, Any]]:
        raw_specs = saved_data.get("request_filters")
        if not isinstance(raw_specs, dict):
            return {}

        field_names = {f.name for f in ModelCls._meta.get_fields()}
        allowed_lookups = ALLOWED_LOOKUPS
        normalized: Dict[str, Dict[str, Any]] = {}
        for param_name, spec in raw_specs.items():
            if not isinstance(param_name, str) or not param_name.strip():
                continue
            if isinstance(spec, str):
                spec = {"field": spec}
            if not isinstance(spec, dict):
                continue

            field_name = str(spec.get("field") or "").strip()
            lookup = str(spec.get("lookup") or "exact").strip()
            if field_name not in field_names or lookup not in allowed_lookups:
                continue

            normalized[param_name.strip()] = {
                "field": field_name,
                "lookup": lookup,
            }
        return normalized

    def _saved_request_filters(
        self,
        request,
        saved_data: Dict[str, Any],
        ModelCls,
    ) -> tuple[Dict[str, Any], Set[str]]:
        specs = self._request_filter_specs(saved_data, ModelCls)
        if not specs:
            return {}, set()

        field_types = self._field_types(ModelCls)
        filters: Dict[str, Any] = {}
        consumed: Set[str] = set()
        for param_name, spec in specs.items():
            raw_value = request.query_params.get(param_name)
            if raw_value in (None, ""):
                continue
            field_name = spec["field"]
            lookup = spec["lookup"]
            key = field_name if lookup == "exact" else f"{field_name}__{lookup}"
            filters[key] = self._coerce_filter_value(field_types.get(field_name, ""), raw_value, lookup)
            consumed.add(param_name)

        return filters, consumed

    def _saved_request_keyword(self, request, saved_data: Dict[str, Any]) -> Optional[str]:
        request_keyword = saved_data.get("request_keyword")
        if isinstance(request_keyword, str):
            candidate = (request.query_params.get(request_keyword) or "").strip()
            return candidate or None
        return None

    def _parse_filters(self, request, model_key: str, ModelCls, reserved_keys: Optional[Set[str]] = None) -> Dict[str, Any]:
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
        field_types = self._field_types(ModelCls)
        reserved_keys = reserved_keys or set()

        def _resolve_parent_field() -> Optional[str]:
            parent_candidates = (
                'proposal', 'order', 'invoice', 'purchase',
                'workorder', 'receipt', 'requisition'
            )
            for candidate in parent_candidates:
                if candidate in field_names:
                    return candidate
            return None
        
        logger.info(f"[_parse_filters] model_key={model_key}, query_params={dict(request.query_params)}")
        
        for key, value in request.query_params.items():
            # Skip reserved parameters
            if key in {'model_name', 'id', 'fields', 'limit', 'offset', 'page', 'page_size', 
                    'q', 'search', 'keyword', 'search_fields', 'saved_search', 'saved_search_name',
                    'saved_search_id', 'search_id', 'order_by', 'ordering'}:
                continue
            if key in reserved_keys:
                continue

            # model_name_filter → filter by the model_name column
            # (model_name is reserved as the wcapi table selector, so models
            # that have a model_name column use this alias to filter by it)
            if key == 'model_name_filter' and 'model_name' in field_names:
                key = 'model_name'

            # Map generic parent filters to the actual FK field on line models
            if key in {'parent', 'parent_id'}:
                parent_field = _resolve_parent_field()
                if parent_field:
                    key = parent_field
            
            # Validate field name (before __lookup)
            field_base = key.split('__')[0]
            # Django FK fields: parent_item_id → parent_item is the field name
            if field_base not in field_names and field_base.endswith('_id'):
                fk_name = field_base[:-3]  # strip _id suffix
                if fk_name in field_names:
                    field_base = fk_name
                    key = fk_name + ('__' + key.split('__')[1] if '__' in key else '')
            if field_base not in field_names:
                continue
            
            # Support common lookup formats
            lookup_type = 'exact'
            if '__' in key:
                lookup_type = key.split('__')[1]
                if lookup_type not in ALLOWED_LOOKUPS:
                    continue
                
                # Handle 'ne' (not equal) by converting to Q object later
                if lookup_type == 'ne':
                    # Store for later Q object handling
                    filters[key] = self._coerce_filter_value(field_types.get(field_base, ''), value, lookup_type)
                    continue

            coerced = self._coerce_filter_value(field_types.get(field_base, ''), value, lookup_type)

            # User searching for "" on a nullable field means "find nulls"
            if coerced == '' and lookup_type == 'exact':
                filter_key = field_base + '__isnull'
                filters[filter_key] = True
            else:
                filters[key] = coerced

        logger.info(f"[_parse_filters] Parsed filters: {filters}")
        return filters

    def _is_admin_user(self, request) -> bool:
        user = getattr(request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            return False
        return bool(
            getattr(user, "is_superuser", False)
            or getattr(user, "is_staff", False)
            or str(getattr(user, "role", "")).lower() == "admin"
        )

    def _validate_search_fields(self, ModelCls, raw_fields: Any) -> List[str]:
        if raw_fields is None:
            return []

        if isinstance(raw_fields, str):
            requested = [f.strip() for f in raw_fields.split(",") if f.strip()]
        elif isinstance(raw_fields, list):
            requested = [str(f).strip() for f in raw_fields if str(f).strip()]
        else:
            return []

        allowed_types = {"CharField", "TextField", "EmailField", "URLField", "SlugField"}
        valid: List[str] = []

        for name in requested:
            try:
                field_obj = ModelCls._meta.get_field(name)
                internal = field_obj.get_internal_type() if hasattr(field_obj, "get_internal_type") else ""
                if internal in allowed_types and name not in valid:
                    valid.append(name)
            except Exception:
                continue

        return valid

    def _parse_search_fields(self, request, ModelCls) -> List[str]:
        raw = request.query_params.get("search_fields")
        return self._validate_search_fields(ModelCls, raw)

    def _normalize_saved_filters(self, raw_filters: Any, ModelCls) -> Dict[str, Any]:
        if not isinstance(raw_filters, dict):
            return {}

        field_names = {f.name for f in ModelCls._meta.get_fields()}
        allowed_lookups = ALLOWED_LOOKUPS

        normalized: Dict[str, Any] = {}
        for key, value in raw_filters.items():
            if not isinstance(key, str) or not key:
                continue
            field_base = key.split("__")[0]
            if field_base not in field_names:
                continue
            if "__" in key:
                lookup_type = key.split("__", 1)[1]
                if lookup_type not in allowed_lookups:
                    continue
            normalized[key] = value
        return normalized

    def _resolve_saved_search(self, request, model_key: str) -> Optional[Dict[str, Any]]:
        search_id = request.query_params.get("saved_search_id") or request.query_params.get("search_id")
        search_name = request.query_params.get("saved_search") or request.query_params.get("saved_search_name")

        if not search_id and not search_name:
            return None

        # Primary source: Report records (category='list', output_type='screen')
        from apps.core.models.report import Report

        rpt_qs = Report.objects.filter(
            is_active=True,
            model_name=model_key,
        )

        if search_id:
            if not str(search_id).isdigit():
                raise ValueError("saved_search_id must be numeric")
            rpt_qs = rpt_qs.filter(pk=int(search_id))
        elif search_name:
            rpt_qs = rpt_qs.filter(name=search_name)

        report = rpt_qs.order_by("-dt_modified").first()

        # Fallback: legacy Setting records (purpose='search')
        if not report:
            from apps.core.models.setting import Setting
            setting_qs = Setting.objects.filter(
                is_active=True,
                purpose="search",
                parent_model=model_key,
            )
            if search_id:
                setting_qs = setting_qs.filter(pk=int(search_id))
            elif search_name:
                setting_qs = setting_qs.filter(name=search_name)

            setting = setting_qs.order_by("-dt_modified").first()
            if not setting:
                raise LookupError("saved search not found")

            required_role = str(setting.role or "").strip().lower()
            user_role = str(getattr(getattr(request, "user", None), "role", "") or "").strip().lower()
            role_open = required_role in {"", "all", "*"}
            if not role_open and not self._is_admin_user(request) and user_role != required_role:
                raise PermissionError("saved search is not shared with your role")

            data = setting.config if isinstance(setting.config, dict) else {}
            return {
                "id": setting.id,
                "name": setting.name,
                "role": setting.role,
                "data": data,
                "source": "setting",
            }

        # Report found — check role access
        required_role = str(report.role_required or "").strip().lower()
        user_role = str(getattr(getattr(request, "user", None), "role", "") or "").strip().lower()
        role_open = required_role in {"", "all", "*"}
        if not role_open and not self._is_admin_user(request) and user_role != required_role:
            raise PermissionError("saved search is not shared with your role")

        data = report.config if isinstance(report.config, dict) else {}
        return {
            "id": report.id,
            "name": report.name,
            "role": report.role_required,
            "data": data,
            "source": "report",
        }

    def _parse_search(self, request, model_key: str, ModelCls) -> Optional[str]:
        """
        Get search query from 'q', 'search', or 'keyword' parameter.
        
        Returns search string or None if not provided.
        """
        search_query = (
            request.query_params.get('q')
            or request.query_params.get('search')
            or request.query_params.get('keyword')
            or ''
        ).strip()
        return search_query if search_query else None

    def _apply_search(
        self,
        qs,
        search_query: str,
        model_key: str,
        ModelCls,
        search_fields_override: Optional[List[str]] = None,
    ) -> Any:
        """
        Apply fragment-based search across configured search fields.

        Supports comma-separated fragments with AND logic:
        - Default: ``istartswith`` (prefix match, indexable)
        - ``@`` prefix: ``icontains`` (substring match)
        - ``refs.keywords`` always searched with ``icontains``

        Uses registry config to determine which fields are searchable.
        Falls back to common fields if not configured.
        """
        if not search_query:
            return qs

        from common.search_utils import build_fragment_query

        search_fields = list(search_fields_override or [])

        # Get search fields from registry config
        if not search_fields:
            config = get_registry_config(model_key)
            search_fields = list(config.search_fields) if config and config.search_fields else []

        # Fallback to common searchable fields
        if not search_fields:
            fallback_fields = []
            for f in ModelCls._meta.get_fields():
                if hasattr(f, 'get_internal_type'):
                    ftype = f.get_internal_type()
                    if ftype in {'CharField', 'TextField', 'EmailField', 'URLField', 'SlugField'}:
                        fallback_fields.append(f.name)
                    elif f.name in {'name', 'title', 'email', 'code', 'reference', 'description'}:
                        fallback_fields.append(f.name)
            search_fields = fallback_fields[:10]

        if not search_fields:
            return qs

        try:
            return build_fragment_query(
                qs, search_query, search_fields, ModelCls,
                include_refs_keywords=True,
            )
        except Exception:
            return qs

    def _apply_filters(self, qs, filters: Dict[str, Any]) -> Any:
        """
        Apply validated filters to queryset with proper Q object handling.
        
        Handles both regular filters and 'ne' (not equal) filters.
        """
        if not filters:
            logger.info("[_apply_filters] No filters to apply")
            return qs
        
        # Separate 'ne' filters (not equal)
        ne_filters = {}
        regular_filters = {}
        
        for key, value in filters.items():
            if '__ne' in key:
                ne_filters[key.replace('__ne', '')] = value
            else:
                regular_filters[key] = value
        
        logger.info(f"[_apply_filters] regular_filters={regular_filters}, ne_filters={ne_filters}")
        
        try:
            # Apply regular filters
            if regular_filters:
                qs = qs.filter(**regular_filters)
                logger.info(f"[_apply_filters] Filter applied with {regular_filters}")
            
            # Apply not-equal filters using Q object negation
            for key, value in ne_filters.items():
                qs = qs.exclude(**{key: value})
        except Exception as e:
            # If filtering fails, return the queryset as-is
            logger.error(f"[_apply_filters] Filter failed: {e}")
            pass
        
        return qs

    def _parse_pagination(self, request, defaults: Optional[Dict[str, Any]] = None) -> tuple[int, int]:
        """
        Parse pagination parameters (limit/offset or page/page_size).
        
        Returns (limit, offset) tuple.
        
        Supports:
        - limit + offset: ?limit=50&offset=100
        - page + page_size: ?page=2&page_size=50 (page is 1-indexed)
        """
        # Check for page-based pagination first
        defaults = defaults or {}

        page = request.query_params.get('page')
        page_size = request.query_params.get('page_size')
        if not page and defaults.get('page') is not None:
            page = str(defaults.get('page'))
        if not page_size and defaults.get('page_size') is not None:
            page_size = str(defaults.get('page_size'))
        
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
        limit = request.query_params.get('limit')
        offset = request.query_params.get('offset')
        if limit is None:
            limit = str(defaults.get('limit', '500'))
        if offset is None:
            offset = str(defaults.get('offset', '0'))
        
        try:
            limit_int = min(int(limit), 1000)  # Max 1000 records
            limit_int = max(1, limit_int)
            offset_int = max(0, int(offset))
            return limit_int, offset_int
        except (ValueError, TypeError):
            return 500, 0

    def _validate_ordering(self, ordering: str, ModelCls) -> Optional[str]:
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

        field_name = ordering.lstrip('-')
        field_names = {f.name for f in ModelCls._meta.get_fields()}
        if field_name not in field_names:
            return None

        try:
            ModelCls.objects.active().order_by(ordering)
            return ordering
        except Exception:
            return None

    def _parse_ordering(self, request, model_key: str, ModelCls) -> Optional[str]:
        """
        Parse and validate ordering parameter.
        
        Supports: ?ordering=field_name or ?ordering=-field_name or ?order_by=...
        
        Returns validated ordering string or None.
        """
        ordering = request.query_params.get('ordering') or request.query_params.get('order_by')
        if not ordering:
            return None

        return self._validate_ordering(ordering, ModelCls)

    def _handle(
        self,
        model_key: str,
        record_id: Optional[Any],
        fields: Optional[List[str]],
        request,
    ) -> Response:
        """Main handler for GET requests with full filtering/search/pagination support."""

        # Special-case dashboard model: aggregate a concise snapshot from commonly-used models
        if model_key in {"dashboard", "dash", "home"}:
            return self._dashboard_snapshot(request)
        
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

            # ── RBAC: verify user can see this specific record ──────
            # Same scoping as list queries — external users can only
            # view records linked to their org. Returns empty if the
            # record doesn't pass the role filter. See wcapi-query-scoping.md
            if request.user and request.user.is_authenticated and not request.user.is_superuser:
                role_q = inject_role_filters(request.user, model_key)
                if role_q:
                    ModelCls = type(obj)
                    if not ModelCls.objects.filter(pk=obj.pk).filter(role_q).exists():
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
            try:
                from common.refs.contact_refs import normalize_refs_for_response
                payload["refs"] = normalize_refs_for_response(payload.get("refs"))
            except Exception:
                pass
            
            # For contact records, include communications via FK relationship
            if model_key == 'contact':
                try:
                    from apps.communications.models import Email, Phone, Address, Domain
                    
                    # Fetch communications linked via FK
                    emails_qs = Email.objects.filter(contact_id=obj.pk, is_deleted=False)
                    phones_qs = Phone.objects.filter(contact_id=obj.pk, is_deleted=False)
                    addresses_qs = Address.objects.filter(contact_id=obj.pk, is_deleted=False)
                    domains_qs = Domain.objects.filter(contact_id=obj.pk, is_deleted=False)
                    
                    # Serialize each to dict
                    communications = {
                        'emails': [services.to_dict(e) for e in emails_qs],
                        'phones': [services.to_dict(p) for p in phones_qs],
                        'addresses': [services.to_dict(a) for a in addresses_qs],
                        'domains': [services.to_dict(d) for d in domains_qs],
                    }
                    payload['communications'] = communications
                    logger.info(f"WCAPIGetView: contact {obj.pk} has {len(communications['emails'])} emails, {len(communications['phones'])} phones via FK")
                except Exception as comm_err:
                    logger.warning(f"WCAPIGetView: Failed to load communications for contact {obj.pk}: {comm_err}")
            
            if self._should_include_lines(model_key):
                payload["lines"] = self._collect_lines(obj, model_key, request)
                if "results" in payload and "results" not in field_names and isinstance(payload["results"], list):
                    payload.pop("results", None)
            else:
                if "results" in payload and "results" not in field_names and isinstance(payload["results"], list):
                    payload.pop("results", None)

            if self._normalize_model_key(model_key) == "action":
                payload["attachments"] = self._action_attachments_map([obj.pk]).get(obj.pk, [])
            
            # Apply RBAC field filtering for single record
            if request.user and request.user.is_authenticated:
                payload = filter_response_data(request.user, model_key, payload)

            # Contact detail UI depends on full refs for related links/tags panels.
            # Force canonical refs payload after field projection so React always
            # receives the complete contact.refs structure.
            if self._normalize_model_key(model_key) == "contact":
                try:
                    from common.refs.contact_refs import normalize_refs_for_response
                    payload["refs"] = normalize_refs_for_response(getattr(obj, "refs", {}) or {})
                except Exception:
                    payload["refs"] = getattr(obj, "refs", {}) or {}
            
            return api_response(data={"record": payload}, status_code=status.HTTP_200_OK)

        # List retrieval with filters, search, and pagination
        ModelCls, qs = services.get_queryset(model_key, request=request)

        saved_search = None
        try:
            saved_search = self._resolve_saved_search(request, model_key)
        except LookupError as e:
            return api_response(
                success=False,
                status_code=status.HTTP_404_NOT_FOUND,
                message=str(e),
                error={"code": "saved_search_not_found"},
            )
        except PermissionError as e:
            return api_response(
                success=False,
                status_code=status.HTTP_403_FORBIDDEN,
                message=str(e),
                error={"code": "saved_search_forbidden"},
            )
        except ValueError as e:
            return api_response(
                success=False,
                status_code=status.HTTP_400_BAD_REQUEST,
                message=str(e),
                error={"code": "invalid_saved_search"},
            )

        saved_data = saved_search.get("data") if isinstance(saved_search, dict) else {}
        if not isinstance(saved_data, dict):
            saved_data = {}

        request_keyword = self._saved_request_keyword(request, saved_data)
        saved_request_filters, consumed_filter_params = self._saved_request_filters(request, saved_data, ModelCls)
        relative_filters = self._resolve_relative_period(saved_data.get("relative_period"))
        
        # ── RBAC Query Scoping ──────────────────────────────────────
        # All data flows through wcapi. For external users (customers,
        # vendors, reps), inject_role_filters reads the field_access
        # Setting for this model and adds Q filters that restrict the
        # queryset to only records belonging to the user's org(s).
        #
        # Example: a customer with org_ids.customer=[5,12] querying
        # orders gets: Order.objects.filter(customer_id__in=[5, 12])
        #
        # Superusers bypass all filters. See readmes/wcapi-query-scoping.md
        # ───────────────────────────────────────────────────────────────
        if request.user and request.user.is_authenticated:
            role_q = inject_role_filters(request.user, model_key)
            if role_q:
                qs = qs.filter(role_q)
        
        # Apply search first (before filters for better performance with indexes)
        search_query = self._parse_search(request, model_key, ModelCls)
        if not search_query and request_keyword:
            search_query = request_keyword
        if not search_query and isinstance(saved_data.get("keyword"), str):
            candidate = str(saved_data.get("keyword") or "").strip()
            if candidate:
                search_query = candidate

        request_search_fields = self._parse_search_fields(request, ModelCls)
        saved_search_fields = self._validate_search_fields(ModelCls, saved_data.get("search_fields"))
        effective_search_fields = request_search_fields or saved_search_fields

        if search_query:
            qs = self._apply_search(
                qs,
                search_query,
                model_key,
                ModelCls,
                search_fields_override=effective_search_fields,
            )
        
        # Parse and apply filters
        filters = self._parse_filters(request, model_key, ModelCls, reserved_keys=consumed_filter_params)
        explicit_filter_keys = set(filters.keys())
        saved_filters = self._normalize_saved_filters(saved_data.get("filters"), ModelCls)
        for key, value in saved_filters.items():
            filters.setdefault(key, value)
        for key, value in relative_filters.items():
            filters.setdefault(key, value)
        for key, value in saved_request_filters.items():
            if key not in explicit_filter_keys:
                filters[key] = value
        qs = self._apply_filters(qs, filters)
        
        # Get total count before pagination
        total_count = qs.count()
        
        # Parse and apply ordering
        ordering = self._parse_ordering(request, model_key, ModelCls)
        if not ordering and isinstance(saved_data.get("ordering"), str):
            ordering = self._validate_ordering(saved_data.get("ordering"), ModelCls)
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
        pagination_defaults: Dict[str, Any] = {}
        if isinstance(saved_data.get("pagination"), dict):
            pagination_defaults.update(saved_data.get("pagination") or {})
        for key in ("limit", "offset", "page", "page_size"):
            if saved_data.get(key) is not None and key not in pagination_defaults:
                pagination_defaults[key] = saved_data.get(key)

        limit, offset = self._parse_pagination(request, defaults=pagination_defaults)
        
        # Apply pagination
        qs_paginated = qs[offset:offset + limit]
        items = list(qs_paginated)
        
        # Serialize results
        allow = policy.field_allowlist(ModelCls, request=request) if ModelCls else None
        results = []
        for obj in items:
            payload = services.to_dict(obj, allow=allow)
            try:
                from common.refs.contact_refs import normalize_refs_for_response
                payload["refs"] = normalize_refs_for_response(payload.get("refs"))
            except Exception:
                pass
            # Apply RBAC field filtering
            if request.user and request.user.is_authenticated:
                payload = filter_response_data(request.user, model_key, payload)
            results.append(payload)

        if self._normalize_model_key(model_key) == "action":
            action_ids = [obj.pk for obj in items if isinstance(getattr(obj, "pk", None), int)]
            attachment_map = self._action_attachments_map(action_ids)
            for payload in results:
                action_id = payload.get("id")
                if isinstance(action_id, int):
                    payload["attachments"] = attachment_map.get(action_id, [])
        
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
                "search_fields": effective_search_fields,
                "filters": filters,
                "ordering": ordering,
                "pagination": {"limit": limit, "offset": offset},
                "saved_search": {
                    "id": saved_search.get("id") if saved_search else None,
                    "name": saved_search.get("name") if saved_search else None,
                    "role": saved_search.get("role") if saved_search else None,
                },
                "request_keyword": request_keyword,
            }
        
        return api_response(data=response_data, status_code=status.HTTP_200_OK)

    def _dashboard_snapshot(self, request) -> Response:
        def safe_count(model_key: str, filters: Optional[Dict[str, Any]] = None) -> Optional[int]:
            try:
                ModelCls, qs = services.get_queryset(model_key, request=request)
                if filters:
                    qs = qs.filter(**filters)
                return qs.count()
            except Exception:
                return None

        def safe_recent(model_key: str, limit: int = 5) -> List[Dict[str, Any]]:
            try:
                ModelCls, qs = services.get_queryset(model_key, request=request)
            except Exception:
                return []

            # Exclude status 'on hold' for actions
            if model_key == "action":
                qs = qs.exclude(status="on hold")

            try:
                qs = qs.order_by("-dt_created")
            except Exception:
                try:
                    qs = qs.order_by("-id")
                except Exception:
                    pass

            items = list(qs[:limit])
            results: List[Dict[str, Any]] = []
            for obj in items:
                try:
                    allow = policy.field_allowlist(type(obj), request=request)
                    payload = services.to_dict(obj, allow=allow)
                except Exception:
                    payload = {}
                if not isinstance(payload, dict):
                    payload = {}

                title = payload.get("name") or payload.get("title") or payload.get("code") or payload.get("reference")
                if not title:
                    ident = payload.get("id") or getattr(obj, "pk", None)
                    title = f"{model_key} #{ident}" if ident else model_key

                meta = payload.get("status") or payload.get("state") or payload.get("owner") or payload.get("assigned_to")
                detail = payload.get("description") or payload.get("note") or payload.get("summary")
                when = payload.get("dt_created") or payload.get("created_at") or payload.get("dt_modified")

                results.append(
                    {
                        "title": title,
                        "meta": meta or "",
                        "detail": detail or "",
                        "time": when,
                        "severity": payload.get("priority") or payload.get("severity"),
                        "owner": payload.get("owner") or payload.get("assigned_to"),
                    }
                )
            return results

        stats = []
        for label, model_key, filters in [
            ("Orders", "order", None),
            ("Invoices", "invoice", None),
            ("Proposals", "proposal", None),
            ("Contacts", "contact", None),
        ]:
            count_val = safe_count(model_key, filters)
            if count_val is not None:
                stats.append({"label": label, "value": count_val})

        # Activities: prefer transactional signals first
        activities = safe_recent("order", limit=5) or safe_recent("proposal", limit=5) or []

        # Notifications: reuse activities but keep lightweight; can be swapped to a dedicated model if available
        notifications = safe_recent("communication", limit=5) or safe_recent("support_ticket", limit=5) or activities[:5]

        # Actions: attempt to surface tasks/assignments
        actions = safe_recent("action", limit=5) or safe_recent("task", limit=5)

        # Quick shortcuts: synthesize from available models
        shortcuts = []
        for label, to in [
            ("Create Order", "/orders/create"),
            ("New Proposal", "/proposals/create"),
            ("Add Contact", "/contacts/create"),
            ("Open Tasks", "/tasks"),
        ]:
            shortcuts.append({"label": label, "to": to})

        payload = {
            "stats": stats,
            "notifications": notifications,
            "activities": activities,
            "actions": actions,
            "shortcuts": shortcuts,
            "pulse": {
                "orders": stats[0]["value"] if len(stats) > 0 else 0,
                "invoices": stats[1]["value"] if len(stats) > 1 else 0,
            },
        }

        return api_response(data=payload, status_code=status.HTTP_200_OK)

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
    - ?q=search_term or ?search=search_term or ?keyword=search_term
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
                description="Model key from WCAPI registry (e.g., 'contact', 'invoice', 'order')",
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
                name="keyword",
                type=str,
                required=False,
                location=OpenApiParameter.QUERY,
                description="Alias for search query (comma-separated terms supported with AND semantics)",
            ),
            OpenApiParameter(
                name="search_fields",
                type=str,
                required=False,
                location=OpenApiParameter.QUERY,
                description="Comma-separated text fields to search (overrides model default search field set)",
            ),
            OpenApiParameter(
                name="saved_search_id",
                type=int,
                required=False,
                location=OpenApiParameter.QUERY,
                description="Apply a stored search Setting by ID (purpose=search, parent_model=model_name)",
            ),
            OpenApiParameter(
                name="saved_search",
                type=str,
                required=False,
                location=OpenApiParameter.QUERY,
                description="Apply a stored search Setting by name (purpose=search)",
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

        # Extract record_id from query params or request body
        record_id = request.query_params.get("id")
        if record_id is None:
            # Check request body for id field
            try:
                if request.content_type and 'application/json' in request.content_type:
                    import json
                    body_data = json.loads(request.body.decode('utf-8'))
                    record_id = body_data.get('id')
                    if record_id is None and 'data' in body_data:
                        record_id = body_data['data'].get('id')
            except (json.JSONDecodeError, UnicodeDecodeError, KeyError):
                pass
        
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
        from apps.core.constants.model_registry import MODEL_REGISTRY
        # Use registry keys — these are the canonical names used in URLs and wcapi
        model_names = sorted(MODEL_REGISTRY.keys())
        return Response({
            "status": "success",
            "code": 200,
            "message": "OK",
            "data": {"model_names": model_names, "count": len(model_names)}
        }, status=status.HTTP_200_OK)


class SearchPresetListView(APIView):
    """List role-visible saved searches (Setting purpose=search) for a model."""

    http_method_names = ["get", "options", "head"]

    @staticmethod
    def _is_admin_user(user) -> bool:
        if not user or not getattr(user, "is_authenticated", False):
            return False
        return bool(
            getattr(user, "is_superuser", False)
            or getattr(user, "is_staff", False)
            or str(getattr(user, "role", "")).lower() == "admin"
        )

    @extend_schema(
        operation_id="search_preset_list",
        summary="List saved search presets",
        description=(
            "Returns saved search presets for a model (Setting purpose=search). "
            "Non-admin users see role-matching and global presets; admins see all."
        ),
        parameters=[
            OpenApiParameter(
                name="model_name",
                type=str,
                required=True,
                location=OpenApiParameter.QUERY,
                description="Canonical model key (for example: customer, item, invoice)",
            ),
        ],
        responses={
            200: inline_serializer(
                name="SearchPresetListResponse",
                fields={
                    "results": serializers.ListField(child=serializers.JSONField()),
                    "count": serializers.IntegerField(),
                    "model_name": serializers.CharField(),
                },
            ),
            400: inline_serializer(
                name="SearchPresetListErrorResponse",
                fields={"detail": serializers.CharField()},
            ),
        },
    )
    def get(self, request, **kwargs):
        model_key = (request.query_params.get("model_name") or "").strip().lower()
        if not model_key:
            return api_response(
                success=False,
                status_code=status.HTTP_400_BAD_REQUEST,
                message="model_name parameter is required",
                error={"code": "missing_model_name"},
            )

        user = getattr(request, "user", None)
        is_admin = self._is_admin_user(user)
        user_role = str(getattr(user, "role", "") or "").strip()

        presets = []

        # Primary: Report records (the new home for shared searches)
        from apps.core.models.report import Report

        rpt_qs = Report.objects.filter(
            is_active=True,
            model_name=model_key,
        )
        if not is_admin:
            rpt_qs = rpt_qs.filter(
                Q(role_required__isnull=True)
                | Q(role_required="")
                | Q(role_required="*")
                | Q(role_required__iexact="all")
                | (Q(role_required__iexact=user_role) if user_role else Q())
            )

        for report in rpt_qs.order_by("sort_order", "name"):
            payload = report.config if isinstance(report.config, dict) else {}
            presets.append(
                {
                    "id": report.id,
                    "name": report.name,
                    "role": report.role_required,
                    "model_name": report.model_name,
                    "source": "report",
                    "output_type": report.output_type,
                    "category": report.category,
                    "keyword": payload.get("keyword"),
                    "search_fields": payload.get("search_fields"),
                    "filters": payload.get("filters"),
                    "ordering": payload.get("ordering"),
                    "pagination": payload.get("pagination"),
                    "request_keyword": payload.get("request_keyword"),
                    "request_filters": payload.get("request_filters"),
                    "relative_period": payload.get("relative_period"),
                    "dt_modified": getattr(report, "dt_modified", None),
                }
            )

        # Fallback: legacy Setting records (purpose='search')
        from apps.core.models import Setting

        setting_qs = Setting.objects.filter(
            is_active=True,
            purpose="search",
            parent_model=model_key,
        )
        if not is_admin:
            role_filters = (
                Q(role__isnull=True)
                | Q(role="")
                | Q(role="*")
                | Q(role__iexact="all")
            )
            if user_role:
                role_filters |= Q(role__iexact=user_role)
            setting_qs = setting_qs.filter(role_filters)

        for setting in setting_qs.order_by("name", "-dt_modified"):
            payload = setting.config if isinstance(setting.config, dict) else {}
            presets.append(
                {
                    "id": setting.id,
                    "name": setting.name,
                    "role": setting.role,
                    "model_name": setting.parent_model,
                    "source": "setting",
                    "keyword": payload.get("keyword"),
                    "search_fields": payload.get("search_fields"),
                    "filters": payload.get("filters"),
                    "ordering": payload.get("ordering"),
                    "pagination": payload.get("pagination"),
                    "request_keyword": payload.get("request_keyword"),
                    "request_filters": payload.get("request_filters"),
                    "relative_period": payload.get("relative_period"),
                    "dt_modified": getattr(setting, "dt_modified", None),
                }
            )

        return api_response(
            data={
                "results": presets,
                "count": len(presets),
                "model_name": model_key,
            },
            status_code=status.HTTP_200_OK,
        )


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


class WCAPIGetViewWithModel(APIView):
    """
    WCAPI get view that accepts model_name in the URL path.
    Supports URLs like /wcapi/<model_name>/get or /wcapi/get/<model_name>
    """
    http_method_names = ["get", "options", "head"]

    def get(self, request, model_name=None, *args, **kwargs):
        # Get model_name from URL path, fallback to query param if not provided
        if not model_name:
            model_name = request.query_params.get("model_name")

        if not model_name:
            return Response(
                {"detail": "model_name parameter is required (in URL or query params)"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Extract record_id from query params or request body
        record_id = request.query_params.get("id")
        if record_id is None:
            # Check request body for id field
            try:
                if request.content_type and 'application/json' in request.content_type:
                    import json
                    body_data = json.loads(request.body.decode('utf-8'))
                    record_id = body_data.get('id')
                    if record_id is None and 'data' in body_data:
                        record_id = body_data['data'].get('id')
            except (json.JSONDecodeError, UnicodeDecodeError, KeyError):
                pass

        # Inject model_name into the existing request's query params
        request.query_params._mutable = True
        request.query_params['model_name'] = model_name
        request.query_params._mutable = False

        # Delegate to the main WCAPIGetView
        view_instance = WCAPIGetView()
        return view_instance.get(request, *args, **kwargs)
