from typing import Optional, Any, cast
import json
from uuid import uuid4

from django.http import Http404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.wcapi.mixins import SettingsDrivenCRUDMixin


class RESTOpenQueryView(SettingsDrivenCRUDMixin, APIView):
    http_method_names = ["post", "options", "head"]

    def serialize_with_view_allowlist(self, obj, request=None, ctx: str = "list"):
        """
        Serialize a model instance using the current view allowlist.
        Falls back to simple getattr lookups if model_to_dict is unavailable.
        """
        model_cls = obj.__class__
        view_fields, _, _, _ = self.get_view_edit_allowlists(model_cls, request=request, ctx=ctx)
        fields_arg = view_fields if view_fields is not None else None
        try:
            from django.forms.models import model_to_dict
            return model_to_dict(obj, fields=fields_arg)
        except Exception:
            data = {}
            if view_fields is None:
                meta = getattr(model_cls, "_meta", None)
                if meta and hasattr(meta, "get_fields"):
                    iter_fields = [
                        f.name
                        for f in meta.get_fields()
                        if getattr(f, "concrete", False) and not getattr(f, "many_to_many", False)
                    ]
                else:
                    iter_fields = []
            else:
                try:
                    iter_fields = list(view_fields)
                except Exception:
                    iter_fields = []
            for name in iter_fields:
                try:
                    data[name] = getattr(obj, name, None)
                except Exception:
                    data[name] = None
            if "id" not in data:
                data["id"] = getattr(obj, "id", getattr(obj, "pk", None))
            return data

    def _model_class(self, model_slug: str):
        # Reuse router’s model resolver
        from apps.core.wcapi.views import RESTModelRouterView
        return RESTModelRouterView()._model_class(model_slug)

    def _json_body(self, request) -> dict:
        # Prefer DRF parsing when available
        try:
            if hasattr(request, "data"):
                data = request.data  # may raise ParseError; DRF handles content-type
                if isinstance(data, dict):
                    return data
        except Exception:
            pass
        # Raw JSON body
        try:
            raw = (getattr(request, "body", b"") or b"").decode() or ""
            if raw.strip():
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    return parsed
        except Exception:
            pass
        # Fallback to form-encoded
        try:
            return dict(getattr(request, "POST", {}).items())
        except Exception:
            return {}

    def _coerce_payload(self, body: dict) -> dict:
        body = dict(body or {})
        # Normalize nested fields possibly sent as strings
        for key in ("dsl", "scope"):
            v = body.get(key)
            if isinstance(v, str):
                try:
                    body[key] = json.loads(v)
                except Exception:
                    body[key] = {}
        if not isinstance(body.get("dsl"), dict):
            body["dsl"] = {}
        if not isinstance(body.get("scope"), dict):
            body["scope"] = {}
        labels = body.get("labels")
        if isinstance(labels, str):
            try:
                labels = json.loads(labels)
            except Exception:
                labels = [labels]
        if not isinstance(labels, list):
            labels = []
        body["labels"] = labels
        name = (body.get("name") or "").strip()
        body["name"] = name
        comment = body.get("comment")
        body["comment"] = "" if comment is None else str(comment)
        return body

    def _mark_skip_envelope(self, request, resp):
        # Ensure our AutoEnvelopeMiddleware skips wrapping
        try:
            setattr(request, "_skip_envelope", True)
        except Exception:
            pass
        for attr in ("_skip_envelope", "skip_envelope", "_envelope_skip"):
            try:
                setattr(resp, attr, True)
            except Exception:
                pass
        try:
            resp["X-Skip-Envelope"] = "skip"
        except Exception:
            pass
        return resp

    def post(self, request, model: Optional[str] = None, *args, **kwargs):
        action = kwargs.get("action")
        model_value = model if model is not None else kwargs.get("model")
        if not model_value:
            raise Http404("Missing model")
        model_slug = str(model_value)
        model_cls = self._model_class(model_slug)

        if action == "save":
            body_raw = self._json_body(request)
            body = self._coerce_payload(body_raw)
            name = body["name"]; dsl = body["dsl"]; scope = body["scope"]; labels = body["labels"]; comment = body["comment"]
            if not name or not isinstance(dsl, dict) or not isinstance(scope, dict):
                return Response({"ok": False, "error": "name, dsl, scope required"}, status=status.HTTP_400_BAD_REQUEST)
            owner_id = getattr(getattr(request, "user", None), "id", None)
            try:
                from apps.core.models import Setting
                row = Setting.objects.create(
                    is_active=True,
                    name=name,
                    purpose="saved_query",
                    role=scope.get("type", "all"),
                    model_name=model_slug,
                    data={"dsl": dsl, "scope": scope, "labels": labels, "owner_id": owner_id, "comment": comment},
                )
                resp = Response({"ok": True, "id": row.id, "name": row.name}, status=status.HTTP_200_OK)
                return self._mark_skip_envelope(request, resp)
            except Exception as e:
                fallback_id = str(uuid4())
                resp = Response(
                    {"ok": True, "id": fallback_id, "name": name, "meta": {"persisted": False, "reason": str(e)}},
                    status=status.HTTP_200_OK,
                )
                return self._mark_skip_envelope(request, resp)
        # ...existing code...


class RESTSavedSetView(SettingsDrivenCRUDMixin, APIView):
    http_method_names = ["post", "patch", "get", "delete", "options", "head"]

    def serialize_with_view_allowlist(self, obj, request=None, ctx: str = "list"):
        """
        Serialize a model instance using the current view allowlist.
        Falls back to simple getattr lookups if model_to_dict is unavailable.
        """
        model_cls = obj.__class__
        view_fields, _, _, _ = self.get_view_edit_allowlists(model_cls, request=request, ctx=ctx)
        fields_arg = view_fields if view_fields is not None else None
        try:
            from django.forms.models import model_to_dict
            return model_to_dict(obj, fields=fields_arg)
        except Exception:
            data = {}
            if view_fields is None:
                meta = getattr(model_cls, "_meta", None)
                if meta and hasattr(meta, "get_fields"):
                    iter_fields = [
                        f.name
                        for f in meta.get_fields()
                        if getattr(f, "concrete", False) and not getattr(f, "many_to_many", False)
                    ]
                else:
                    iter_fields = []
            else:
                try:
                    iter_fields = list(view_fields)
                except Exception:
                    iter_fields = []
            for name in iter_fields:
                try:
                    data[name] = getattr(obj, name, None)
                except Exception:
                    data[name] = None
            if "id" not in data:
                data["id"] = getattr(obj, "id", getattr(obj, "pk", None))
            return data

    def _model_class(self, model_slug: str):
        from apps.core.wcapi.views import RESTModelRouterView
        return RESTModelRouterView()._model_class(model_slug)

    def _json_body(self, request):
        try:
            import json
            return json.loads(request.body.decode() or "{}")
        except Exception:
            return {}

    def apply_role_scope(self, qs: Any, request, meta, roles) -> Any:
        # Delegate to mixin implementation if present; otherwise no-op.
        mixin_impl = getattr(SettingsDrivenCRUDMixin, "apply_role_scope", None)
        if callable(mixin_impl):
            return mixin_impl(self, qs, request, meta, roles)
        return qs

    def _mark_skip_envelope(self, request, resp):
        try:
            setattr(request, "_skip_envelope", True)
        except Exception:
            pass
        for attr in ("_skip_envelope", "skip_envelope", "_envelope_skip"):
            try:
                setattr(resp, attr, True)
            except Exception:
                pass
        try:
            resp["X-Skip-Envelope"] = "skip"
        except Exception:
            pass
        return resp

    def post(self, request, model: Optional[str] = None, *args, **kwargs):
        from apps.core.models import Setting
        model_slug = model or kwargs.get("model")
        if not model_slug:
            raise Http404("Missing model")
        body = self._json_body(request)
        name = (body.get("name") or "").strip()
        ids = list(body.get("ids") or [])
        scope = body.get("scope") or {}
        labels = body.get("labels") or []
        comment = body.get("comment") or ""
        if not name or not isinstance(ids, list) or not isinstance(scope, dict):
            return Response({"ok": False, "error": "name, ids, scope required"}, status=status.HTTP_400_BAD_REQUEST)
        owner_id = getattr(getattr(request, "user", None), "id", None)
        row = Setting.objects.create(
            is_active=True,
            name=name,
            purpose="saved_set",
            role=scope.get("type", "all"),
            model_name=model_slug,
            data={"ids": ids, "scope": scope, "labels": labels, "owner_id": owner_id, "comment": comment},
        )
        resp = Response({"ok": True, "id": row.id, "name": row.name, "count": len(ids)}, status=status.HTTP_200_OK)
        return self._mark_skip_envelope(request, resp)

    def patch(self, request, model: Optional[str] = None, ident: Optional[str] = None, *args, **kwargs):
        model_slug = model or kwargs.get("model")
        if not model_slug:
            raise Http404("Missing model")
        ident_value = ident if ident is not None else kwargs.get("ident")
        row = self._load_saved_set_setting(request, model_slug, str(ident_value))
        if not self._can_access_saved_setting(request, row):
            return Response({"detail": "forbidden"}, status=status.HTTP_403_FORBIDDEN)

        body = self._json_body(request)
        op = (body.get("op") or "").lower()
        ids = list(body.get("ids") or [])
        data = getattr(row, "data", {}) or {}
        current = list((data.get("ids") or []))

        if op == "add":
            new_ids = list({*current, *ids})
        elif op == "remove":
            new_ids = [i for i in current if i not in set(ids)]
        elif op == "replace":
            new_ids = ids
        elif op == "clear":
            new_ids = []
        else:
            return Response({"detail": "op must be add|remove|replace|clear"}, status=status.HTTP_400_BAD_REQUEST)

        data["ids"] = new_ids
        row.data = cast(Any, data)
        row.save(update_fields=["data"])
        resp = Response({"ok": True, "id": row.id, "count": len(new_ids)}, status=status.HTTP_200_OK)
        return self._mark_skip_envelope(request, resp)

    def get(self, request, model: Optional[str] = None, ident: Optional[str] = None, *args, **kwargs):
        model_val = model if model is not None else kwargs.get("model")
        if not model_val:
            raise Http404("Missing model")
        model_slug = str(model_val)
        ident_value = ident if ident is not None else kwargs.get("ident")
        row = self._load_saved_set_setting(request, model_slug, str(ident_value))
        model_cls = self._model_class(model_slug)
        view_fields, _, _, meta = self.get_view_edit_allowlists(model_cls, request=request, ctx="list")
        ids = list(((getattr(row, "data", {}) or {}).get("ids") or []))
        qs = self.base_queryset(model_cls)
        qs = self.apply_role_scope(qs, request, meta, self._roles_for(request))
        qs = cast(Any, qs)
        qs = qs.filter(pk__in=ids) if ids else qs.none()
        data = [self.serialize_with_view_allowlist(o, request=request, ctx="list") for o in qs]
        resp = Response({"ok": True, "data": data, "items": data, "meta": {"count": len(data)}}, status=status.HTTP_200_OK)
        return self._mark_skip_envelope(request, resp)

    def delete(self, request, model: Optional[str] = None, ident: Optional[str] = None, *args, **kwargs):
        model_slug = model or kwargs.get("model")
        if not model_slug:
            raise Http404("Missing model")
        ident_value = ident if ident is not None else kwargs.get("ident")
        row = self._load_saved_set_setting(request, model_slug, str(ident_value))
        if not self._can_access_saved_setting(request, row):
            return Response({"detail": "forbidden"}, status=status.HTTP_403_FORBIDDEN)
        row.delete()
        resp = Response({"ok": True, "deleted": True}, status=status.HTTP_200_OK)
        return self._mark_skip_envelope(request, resp)