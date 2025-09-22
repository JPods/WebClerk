from __future__ import annotations
from typing import Any, Dict, List, Optional, cast, TYPE_CHECKING
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
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.http import JsonResponse, Http404
from apps.core.wcapi.mixins import SettingsDrivenCRUDMixin

try:
    from apps.core.wcapi import model_policies as mp
except Exception:
    mp = None

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

class RESTModelRouterView(SettingsDrivenCRUDMixin, APIView):
    """
    Canonical REST:
      - GET /<model>/            -> list (wcapi get)
      - GET /<model>/<id>/       -> single (wcapi get)
      - POST /<model>/<id>/      -> update (routes to wcapi save)
      - DELETE /<model>/<id>/    -> delete single (wcapi delete)
      - DELETE /<model>/         -> batch delete via body (ids or filters)
    Creation: POST /wcapi/save.
    """
    if TYPE_CHECKING:
        # Stubs for methods provided by SettingsDrivenCRUDMixin; for type checkers only.
        def serialize_with_view_allowlist(self, obj: Any, request: Any, ctx: str) -> Dict[str, Any]: ...
        def get_view_edit_allowlists(self, model_cls: Any, request: Any, ctx: str, view_name: Optional[str] = ...) -> tuple[Any, Any, Any, Dict[str, Any]]: ...
        def sanitize_payload_with_edit_allowlist(self, model_cls: Any, payload: Dict[str, Any], request: Any, ctx: str) -> tuple[Dict[str, Any], Dict[str, Any]]: ...
        def _save(self, model_cls: Any, payload: Dict[str, Any], pk: Optional[Any] = ...) -> Any: ...
        def _roles_for(self, request: Any): ...
        def base_queryset(self, model_cls: Any): ...
        def apply_filters(self, qs: Any, request: Any, model_cls: Any, view_fields: Any, meta: Dict[str, Any], special_view_name: Optional[str] = ...) -> Any: ...
        def apply_keyword_search(self, qs: Any, request: Any, meta: Dict[str, Any]) -> Any: ...
        def apply_search(self, qs: Any, request: Any, model_cls: Any, meta: Dict[str, Any]) -> Any: ...
        def apply_ordering(self, qs: Any, request: Any, meta: Dict[str, Any]) -> Any: ...
        def paginate(self, qs: Any, request: Any, meta: Dict[str, Any]) -> Any: ...
        def soft_delete(self, obj: Any, meta: Dict[str, Any]) -> bool: ...
        def run_hook(self, hook_name: str, meta: Dict[str, Any], context: Dict[str, Any]) -> None: ...
    def _model_class(self, model_slug: str):
        model_cls = resolve(model_slug) if model_slug else None
        if model_cls is None:
            raise Http404(f"Unknown model: {model_slug}")
        return model_cls

    def _json_body(self, request):
        try:
            import json
            return json.loads(request.body.decode() or "{}")
        except Exception:
            return {}

    def apply_role_scope(self, qs, request, meta, roles):
        """
        Delegate to SettingsDrivenCRUDMixin.apply_role_scope if provided; otherwise, return queryset unchanged.
        """
        super_obj = super()
        if hasattr(super_obj, "apply_role_scope"):
            return super_obj.apply_role_scope(qs, request, meta, roles)  # type: ignore[attr-defined]
        return qs

    # GET list or detail
    def get(self, request, model: Optional[str] = None, pk: Optional[int] = None, *args, **kwargs):
        model_slug = model if isinstance(model, str) else kwargs.get("model")
        if not isinstance(model_slug, str) or not model_slug:
            raise Http404(f"Unknown model: {model_slug}")
        model_cls = self._model_class(model_slug)
        view_name = request.GET.get("name") or request.headers.get("X-View-Name")

        if pk:
            obj = model_cls.objects.get(pk=pk)
            try:
                data = self.serialize_with_view_allowlist(obj, request=request, ctx="display")
                _, _, _, meta = self.get_view_edit_allowlists(model_cls, request=request, ctx="display", view_name=view_name)
            except Exception:
                # Fallback serialization to avoid 500 in legacy paths
                data = services.to_dict(obj)
                meta = {}
            resp = {
                "ok": True,
                "data": {"item": data},   # embed for legacy tests
                "item": data,             # top-level alias
            }
            if meta.get("policy_missing") or meta.get("view_name"):
                resp["meta"] = {
                    "policy_missing": bool(meta.get("policy_missing")),
                    "policy_source": meta.get("policy_source"),
                    "roles_applied": meta.get("roles_applied"),
                    "view_name": meta.get("view_name"),
                }
            return Response(resp, status=status.HTTP_200_OK)

        # Staff-only guard for free-text search (?q=)
        if "q" in request.GET:
            user = getattr(request, "user", None)
            if not (user and (getattr(user, "is_staff", False) or getattr(user, "is_superuser", False))):
                return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

        view_fields, _, _, meta = self.get_view_edit_allowlists(model_cls, request=request, ctx="list", view_name=view_name)
        roles = self._roles_for(request)
        qs = self.base_queryset(model_cls)
        qs = self.apply_role_scope(qs, request, meta, roles)
        qs = self.apply_filters(qs, request, model_cls, view_fields, meta, special_view_name=meta.get("view_name"))
        qs = self.apply_keyword_search(qs, request, meta)
        qs = self.apply_search(qs, request, model_cls, meta)
        page_qs, page_meta = self.paginate(qs, request, meta)
        try:
            data = [self.serialize_with_view_allowlist(o, request=request, ctx="list") for o in page_qs]
        except Exception:
            data = [services.to_dict(o) for o in page_qs]

        resp_meta = dict(page_meta)
        if meta.get("policy_missing") or meta.get("view_name"):
            resp_meta.update({
                "policy_missing": bool(meta.get("policy_missing")),
                "policy_source": meta.get("policy_source"),
                "roles_applied": meta.get("roles_applied"),
                "view_name": meta.get("view_name"),
            })

        payload_data = {"items": data}
        return Response({"ok": True, "data": payload_data, "items": data, "meta": resp_meta}, status=status.HTTP_200_OK)

    def post(self, request, model: Optional[str] = None, pk: Optional[int] = None, *args, **kwargs):
        model_slug = model if isinstance(model, str) else kwargs.get("model")
        if not isinstance(model_slug, str) or not model_slug:
            raise Http404(f"Unknown model: {model_slug}")
        model_cls = self._model_class(model_slug)
        payload = self._json_body(request)
        payload, meta = self.sanitize_payload_with_edit_allowlist(model_cls, payload, request=request, ctx="display")
        self.run_hook("pre_save", meta, {"request": request, "model": model_cls, "payload": payload, "pk": pk})
        obj = self._save(model_cls, payload, pk=pk)
        self.run_hook("post_save", meta, {"request": request, "model": model_cls, "payload": payload, "pk": pk, "obj": obj})
        data = self.serialize_with_view_allowlist(obj, request=request, ctx="display")
        return Response({"ok": True, "data": data, "item": data}, status=status.HTTP_200_OK)

    def delete(self, request, model: Optional[str] = None, pk: Optional[int] = None, *args, **kwargs):
        model_slug = model if isinstance(model, str) else kwargs.get("model")
        if not isinstance(model_slug, str) or not model_slug:
            raise Http404(f"Unknown model: {model_slug}")
        model_cls = self._model_class(model_slug)
        if pk is None:
            raise Http404("Missing pk")
        obj = model_cls.objects.get(pk=pk)
        _, _, _, meta = self.get_view_edit_allowlists(model_cls, request=request, ctx="display")

        self.run_hook("pre_delete", meta, {"request": request, "model": model_cls, "pk": pk, "obj": obj})

        soft = self.soft_delete(obj, meta)
        if not soft:
            obj.delete()

        self.run_hook("post_delete", meta, {"request": request, "model": model_cls, "pk": pk})
        return Response({"ok": True, "deleted": True, "soft": bool(soft)}, status=status.HTTP_200_OK)