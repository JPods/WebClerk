from __future__ import annotations
from typing import Any, Dict, List, Optional
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from . import services, policy
from .registry import resolve
import hashlib
import json
from datetime import datetime, timezone
from email.utils import formatdate, parsedate_to_datetime
from django.utils import timezone as dj_timezone  # added

class WCAPIGetView(APIView):
    http_method_names = ["get", "post", "options", "head"]

    def _handle(self, model_key: str, record_id: Optional[Any], filters: Dict[str, Any], fields: Optional[List[str]], request):
        if not resolve(model_key):
            return Response({"detail": "invalid model"}, status=status.HTTP_400_BAD_REQUEST)
        if record_id is not None:
            obj = services.get_item(model_key, request=request, id=record_id)
            if not obj:
                return Response({"item": None}, status=status.HTTP_200_OK)
            allow = policy.field_allowlist(type(obj), request=request)
            return Response({"item": services.to_dict(obj, allow=allow)}, status=status.HTTP_200_OK)
        items = services.list_items(model_key, request=request, filters=filters or {})
        allow = policy.field_allowlist(type(items[0]), request=request) if items else None
        return Response({"items": [services.to_dict(o, allow=allow) for o in items]}, status=status.HTTP_200_OK)

    def get(self, request, *args, **kwargs):
        # Only accept 'model' query param
        model_key = request.query_params.get("model")
        if not model_key:
            return Response({"detail": "invalid model"}, status=status.HTTP_400_BAD_REQUEST)
        record_id = request.query_params.get("id")
        fields = request.query_params.get("fields")
        fields_list = [f.strip() for f in fields.split(",")] if isinstance(fields, str) else None
        return self._handle(model_key, record_id, {}, fields_list, request)

    def post(self, request, *args, **kwargs):
        # Only accept 'model' in body
        body: Dict[str, Any] = request.data or {}
        model_key = body.get("model")
        record_id = body.get("id")
        filters = body.get("filters") or {}
        fields: Optional[List[str]] = body.get("fields")
        if not model_key:
            return Response({"detail": "invalid model"}, status=status.HTTP_400_BAD_REQUEST)
        return self._handle(model_key, record_id, filters, fields, request)

class WCAPIQueryView(WCAPIGetView):
    def post(self, request, *args, **kwargs):
        body = dict(request.data or {})
        body.pop("id", None)
        request._full_data = body  # type: ignore[attr-defined]
        return super().post(request, *args, **kwargs)

class WCAPISaveView(APIView):
    http_method_names = ["post", "put", "patch", "options", "head"]

    def _handle(self, model_key: Optional[str], record_id: Optional[Any], payload: Dict[str, Any], _fields, request):
        body: Dict[str, Any] = payload or {}
        model = model_key or body.get("model")
        rid = record_id if record_id is not None else body.get("id")
        data = body.get("data") or {}
        if not model or not isinstance(data, dict) or not resolve(model):
            return Response({"detail": "invalid payload"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            pk, action = services.save_item(model, request=request, data=data, id=rid)
        except LookupError:
            return Response({"detail": "not found"}, status=status.HTTP_404_NOT_FOUND)
        status_code = status.HTTP_201_CREATED if action == "created" else status.HTTP_200_OK
        return Response({"id": pk, "action": action}, status=status_code)

    def post(self, request, *args, **kwargs):
        body: Dict[str, Any] = request.data or {}
        model_key = body.get("model")
        record_id = body.get("id")
        return self._handle(model_key, record_id, body, None, request)

    put = post
    patch = post

class WCAPIDeleteView(APIView):
    http_method_names = ["post", "options", "head"]

    def post(self, request, *args, **kwargs):
        body: Dict[str, Any] = request.data or {}
        model_key = body.get("model")
        record_id = body.get("id")
        if not model_key or record_id is None or not resolve(model_key):
            return Response({"detail": "invalid payload"}, status=status.HTTP_400_BAD_REQUEST)
        deleted = services.delete_item(model_key, request=request, id=record_id)
        return Response({"deleted": bool(deleted), "id": record_id}, status=status.HTTP_200_OK)

class RESTModelRouterView(APIView):
    """
    Canonical REST:
      - GET /<model>/            -> list (wcapi get)
      - GET /<model>/<id>/       -> single (wcapi get)
      - POST /<model>/<id>/      -> update (routes to wcapi save)
      - DELETE /<model>/<id>/    -> delete single (wcapi delete)
      - DELETE /<model>/         -> batch delete via body (ids or filters)
    Creation: POST /wcapi/save.
    """
    http_method_names = ["get", "post", "delete", "options", "head"]

    def get(self, request, model: str, pk: Optional[Any] = None, *args, **kwargs):
        # Staff-only search on list endpoints via ?q=...
        if pk is None:
            q = request.query_params.get("q")
            if q and not getattr(request.user, "is_staff", False):
                return Response({"detail": "forbidden"}, status=status.HTTP_403_FORBIDDEN)

        super_get = getattr(super(RESTModelRouterView, self), "get", None)
        resp = super_get(request, model, pk, *args, **kwargs) if callable(super_get) else None
        if resp is None:
            try:
                view = WCAPIGetView()
                resp = view._handle(model, pk, {}, None, request)
            except Exception:
                return Response({"detail": "server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # For list endpoints, paginate and ensure `results` alias exists
        try:
            if pk is None and getattr(resp, "status_code", 200) == 200:
                body = getattr(resp, "data", {}) or {}
                payload = body.get("data", body)

                # Pull full list from items/results
                items = []
                if isinstance(payload, dict):
                    if isinstance(payload.get("items"), list):
                        items = payload.get("items") or []
                    elif isinstance(payload.get("results"), list):
                        items = payload.get("results") or []

                # Apply simple page/page_size pagination (defaults: 25)
                if isinstance(items, list) and items:
                    try:
                        page = int(request.query_params.get("page", "1"))
                    except Exception:
                        page = 1
                    try:
                        page_size = int(request.query_params.get("page_size", "25"))
                    except Exception:
                        page_size = 25
                    page = max(page, 1)
                    page_size = max(min(page_size, 100), 1)  # cap to 100

                    total = len(items)
                    start = (page - 1) * page_size
                    end = start + page_size
                    page_items = items[start:end]

                    # Write paginated payload back; provide both items and results for compatibility
                    payload["count"] = total
                    payload["page"] = page
                    payload["page_size"] = page_size
                    payload["items"] = page_items
                    payload["results"] = page_items
        except Exception:
            pass

        # Add cache headers (ETag, Last-Modified) for detail responses
        try:
            if pk is not None and getattr(resp, "status_code", 200) == 200:
                body = getattr(resp, "data", {}) or {}
                payload = body.get("data", body)
                item = payload.get("item", payload if isinstance(payload, dict) else {})

                etag_hash = hashlib.md5(json.dumps(item, sort_keys=True, default=str).encode("utf-8")).hexdigest()
                etag = f"\"{etag_hash}\""

                lm_dt = None
                try:
                    obj = services.get_item(model, request=request, id=pk)
                except Exception:
                    obj = None
                if obj is not None:
                    for fld in ("dt_modified", "modified", "updated_at", "dt_updated", "dt_created", "created_at", "created"):
                        v = getattr(obj, fld, None)
                        if isinstance(v, datetime):
                            lm_dt = v
                            break
                if lm_dt is None:
                    lm_dt = dj_timezone.now()

                # Normalize to UTC and second precision (HTTP-date granularity)
                if lm_dt.tzinfo is None:
                    lm_dt = lm_dt.replace(tzinfo=timezone.utc)
                else:
                    lm_dt = lm_dt.astimezone(timezone.utc)
                lm_dt_sec = lm_dt.replace(microsecond=0)
                last_modified = formatdate(lm_dt_sec.timestamp(), usegmt=True)

                inm = request.headers.get("If-None-Match") or request.META.get("HTTP_IF_NONE_MATCH")
                if inm and etag in inm:
                    not_mod = Response(status=status.HTTP_304_NOT_MODIFIED)
                    not_mod["ETag"] = etag
                    not_mod["Last-Modified"] = last_modified
                    return not_mod

                ims_raw = request.headers.get("If-Modified-Since") or request.META.get("HTTP_IF_MODIFIED_SINCE")
                if ims_raw:
                    try:
                        ims_dt = parsedate_to_datetime(ims_raw)
                        if ims_dt.tzinfo is None:
                            ims_dt = ims_dt.replace(tzinfo=timezone.utc)
                        else:
                            ims_dt = ims_dt.astimezone(timezone.utc)
                        ims_dt_sec = ims_dt.replace(microsecond=0)
                        if ims_dt_sec >= lm_dt_sec:
                            not_mod = Response(status=status.HTTP_304_NOT_MODIFIED)
                            not_mod["ETag"] = etag
                            not_mod["Last-Modified"] = last_modified
                            return not_mod
                    except Exception:
                        pass

                if isinstance(resp, Response):
                    resp["ETag"] = etag
                    resp["Last-Modified"] = last_modified
        except Exception:
            pass

        return resp

    def post(self, request, model: str, pk: Optional[Any] = None, *args, **kwargs):
        """
        Create (on list) or update (on detail) via WCAPISaveView.
        """
        try:
            payload = request.data if hasattr(request, "data") else {}
        except Exception:
            payload = {}
        try:
            view = WCAPISaveView()
        except NameError:
            from .views import WCAPISaveView as _Save  # avoid circulars
            view = _Save()
        return view._handle(model, pk, payload, None, request)

    def _is_truthy(self, v: Any) -> bool:
        return str(v).strip().lower() in {"1", "true", "t", "yes", "y"}

    def _soft_requested(self, request) -> bool:
        body = getattr(request, "data", {}) or {}
        return self._is_truthy(request.query_params.get("soft") or body.get("soft") or "")

    def _soft_delete_object(self, obj) -> bool:
        """
        Best-effort soft delete:
          - is_deleted: True
          - status: 'deleted'
          - dt_deleted / deleted_at: now()
        Returns True if a soft delete mutation was applied.
        """
        mutated = False
        try:
            if hasattr(obj, "is_deleted"):
                setattr(obj, "is_deleted", True)
                mutated = True
            elif hasattr(obj, "status"):
                try:
                    # Avoid overwriting if already deleted
                    if getattr(obj, "status") != "deleted":
                        setattr(obj, "status", "deleted")
                        mutated = True
                except Exception:
                    pass
            if hasattr(obj, "dt_deleted"):
                setattr(obj, "dt_deleted", dj_timezone.now())
                mutated = True
            elif hasattr(obj, "deleted_at"):
                setattr(obj, "deleted_at", dj_timezone.now())
                mutated = True
            if mutated:
                # Build a safe list of fields to update; fall back to full save if uncertain
                update_fields: List[str] = []
                try:
                    if hasattr(obj, "is_deleted"):
                        update_fields.append("is_deleted")
                    elif hasattr(obj, "status"):
                        update_fields.append("status")
                    if hasattr(obj, "dt_deleted"):
                        update_fields.append("dt_deleted")
                    elif hasattr(obj, "deleted_at"):
                        update_fields.append("deleted_at")
                    # If we didn't determine specific fields, try model _meta safely
                    meta = getattr(obj, "_meta", None)
                    if not update_fields and meta is not None and hasattr(meta, "fields"):
                        update_fields = [f.name for f in meta.fields if hasattr(obj, f.name)]
                except Exception:
                    update_fields = []
                try:
                    if update_fields:
                        obj.save(update_fields=update_fields)
                    else:
                        obj.save()
                except Exception:
                    obj.save()
        except Exception:
            mutated = False
        return mutated

    def delete(self, request, model: str, pk: Optional[Any] = None, *args, **kwargs):
        if not resolve(model):
            return Response({"detail": "invalid model"}, status=status.HTTP_400_BAD_REQUEST)

        soft = self._soft_requested(request)

        if pk is not None:
            if soft:
                obj = services.get_item(model, request=request, id=pk)
                if obj and self._soft_delete_object(obj):
                    return Response({"deleted": True, "id": pk, "soft": True}, status=status.HTTP_200_OK)
            # fallback hard delete
            deleted = services.delete_item(model, request=request, id=pk)
            return Response({"deleted": bool(deleted), "id": pk, "soft": False}, status=status.HTTP_200_OK)

        body: Dict[str, Any] = request.data or {}
        ids = body.get("ids")
        filters = body.get("filters")
        deleted_count = 0

        if isinstance(ids, list) and ids:
            if soft:
                for rid in ids:
                    obj = services.get_item(model, request=request, id=rid)
                    if obj and self._soft_delete_object(obj):
                        deleted_count += 1
            else:
                for rid in ids:
                    if services.delete_item(model, request=request, id=rid):
                        deleted_count += 1
        elif isinstance(filters, dict) and filters:
            try:
                _, qs = services.get_queryset(model, request=request)
            except ValueError:
                return Response({"detail": "invalid model"}, status=status.HTTP_400_BAD_REQUEST)
            if soft:
                for obj in qs.filter(**filters):
                    if self._soft_delete_object(obj):
                        deleted_count += 1
            else:
                for obj in qs.filter(**filters):
                    obj.delete()
                    deleted_count += 1
        else:
            return Response({"detail": "provide ids[] or filters{}"}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"deleted_count": deleted_count, "soft": soft}, status=status.HTTP_200_OK)