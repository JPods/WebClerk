from django.http import JsonResponse, HttpResponseBadRequest, Http404, HttpResponseForbidden
from django.views import View
from django.forms.models import model_to_dict
from apps.core.wcapi.mixins import SettingsDrivenCRUDMixin
from typing import Optional, cast, Any

class RESTOpenQueryView(SettingsDrivenCRUDMixin, View):
    """
    POST /wcapi/<model>/_query
      Body: { where, order_by, joins, limit, offset, saved?: <id|name> }
    POST /wcapi/<model>/_query/save
      Body: { name, dsl: {...}, scope: {type: person|role|job, value}, labels?:[], comment?:"" }
    """
    http_method_names = ["post", "options", "head"]

    def _model_class(self, model_slug: str):
        from apps.core.wcapi.views import RESTModelRouterView
        return RESTModelRouterView()._model_class(model_slug)  # reuse resolver

    def _json_body(self, request):
        try:
            import json
            return json.loads(request.body.decode() or "{}")
        except Exception:
            return {}

    def serialize_with_view_allowlist(self, obj, request=None, ctx="list"):
        model_cls = obj.__class__
        view_fields, _, _, _ = self.get_view_edit_allowlists(model_cls, request=request, ctx=ctx)
        try:
            if view_fields:
                return model_to_dict(obj, fields=view_fields)
            return model_to_dict(obj)
        except Exception:
            return model_to_dict(obj)

    def post(self, request, model: Optional[str] = None, *args, **kwargs):
        action = kwargs.get("action")  # None or "save"
        model_slug_val = (model or kwargs.get("model"))
        if not isinstance(model_slug_val, str) or not model_slug_val:
            return HttpResponseBadRequest("model required")
        model_slug = cast(str, model_slug_val)
        model_cls = self._model_class(model_slug)

        if action == "save":
            body = self._json_body(request)
            name = (body.get("name") or "").strip()
            dsl = body.get("dsl") or {}
            scope = body.get("scope") or {}
            labels = body.get("labels") or []
            comment = body.get("comment") or ""
            if not name or not isinstance(dsl, dict) or not isinstance(scope, dict):
                return HttpResponseBadRequest("name, dsl, scope required")
            try:
                from apps.core.models import Setting
            except Exception:
                return HttpResponseBadRequest("Setting model unavailable")
            # owner metadata
            owner_id = getattr(getattr(request, "user", None), "id", None)
            data = {
                "dsl": dsl,
                "scope": scope,
                "labels": labels,
                "owner_id": owner_id,
            }
            row = Setting.objects.create(
                is_active=True,
                name=name,
                purpose="saved_query",
                role=scope.get("type", "all"),
                model_name=model_slug,
                data=data,
                comment=comment,
            )
            return JsonResponse({"ok": True, "id": row.id, "name": row.name})
        else:
            # Run query (body or saved)
            view_fields, _, _, meta = self.get_view_edit_allowlists(model_cls, request=request, ctx="list")
            body = self._json_body(request)
            saved_ident = (body.get("saved") or request.GET.get("saved") or "").strip()
            if saved_ident:
                try:
                    row = self._load_saved_query_setting(request, model_slug, saved_ident)
                except Http404:
                    return JsonResponse({"ok": True, "data": [], "meta": {"error": "saved query not found"}}, status=404)
                body = (getattr(row, "data", {}) or {}).get("dsl") or {}
            qs, paging = self.evaluate_open_query(model_cls, request, meta)
            # allow saved set filter via ?set=
            qs = self.filter_by_saved_set(qs, request, model_cls, meta)
            data = [self.serialize_with_view_allowlist(o, request=request, ctx="list") for o in qs]
            return JsonResponse({"ok": True, "data": data, "meta": paging})


class RESTSavedSetView(SettingsDrivenCRUDMixin, View):
    """
    Manage saved record id sets for a model via Setting(purpose='saved_set').

    POST /wcapi/<model>/_sets
      Body: { name, ids: [..], scope: {type, value}, labels?:[], comment?:"" }
    PATCH /wcapi/<model>/_sets/<ident>
      Body: { op: add|remove|replace|clear, ids?: [..] }
    GET /wcapi/<model>/_sets/<ident>
      Return serialized records in the set (respects soft-delete + view allowlist)
    DELETE /wcapi/<model>/_sets/<ident>
      Delete the saved set (owner/admin only)
    """
    http_method_names = ["post", "patch", "get", "delete", "options", "head"]

    def _model_class(self, model_slug: str):
        from apps.core.wcapi.views import RESTModelRouterView
        return RESTModelRouterView()._model_class(model_slug)

    def _json_body(self, request):
        try:
            import json
            return json.loads(request.body.decode() or "{}")
        except Exception:
            return {}

    def serialize_with_view_allowlist(self, obj, request=None, ctx="list"):
        model_cls = obj.__class__
        view_fields, _, _, _ = self.get_view_edit_allowlists(model_cls, request=request, ctx=ctx)
        try:
            if view_fields:
                return model_to_dict(obj, fields=view_fields)
            return model_to_dict(obj)
        except Exception:
            return model_to_dict(obj)

    def post(self, request, model: Optional[str] = None, *args, **kwargs):
        try:
            from apps.core.models import Setting
        except Exception:
            return HttpResponseBadRequest("Setting model unavailable")

        model_slug_val = (model or kwargs.get("model"))
        if not isinstance(model_slug_val, str) or not model_slug_val:
            return HttpResponseBadRequest("model required")
        model_slug = cast(str, model_slug_val)
        body = self._json_body(request)

        name = (body.get("name") or "").strip()
        ids = list(body.get("ids") or [])
        scope = body.get("scope") or {}
        labels = body.get("labels") or []
        comment = body.get("comment") or ""
        if not name or not isinstance(ids, list) or not isinstance(scope, dict):
            return HttpResponseBadRequest("name, ids, scope required")

        owner_id = getattr(getattr(request, "user", None), "id", None)
        data = {
            "ids": ids,
            "scope": scope,
            "labels": labels,
            "owner_id": owner_id,
        }
        row = Setting.objects.create(
            is_active=True,
            name=name,
            purpose="saved_set",
            role=scope.get("type", "all"),
            model_name=model_slug,
            data=data,
            comment=comment,
        )
        return JsonResponse({"ok": True, "id": row.id, "count": len(ids)})

    def patch(self, request, model: Optional[str] = None, ident: Optional[str] = None, *args, **kwargs):
        try:
            from apps.core.models import Setting
        except Exception:
            return HttpResponseBadRequest("Setting model unavailable")

        model_slug_val = (model or kwargs.get("model"))
        if not isinstance(model_slug_val, str) or not model_slug_val:
            return HttpResponseBadRequest("model required")
        model_slug = cast(str, model_slug_val)

        ident_val = ident or kwargs.get("ident")
        if ident_val is None or (isinstance(ident_val, str) and not ident_val.strip()):
            return HttpResponseBadRequest("ident required")
        ident_str = str(ident_val)

        row = self._load_saved_set_setting(request, model_slug, ident_str)
        if not self._can_access_saved_setting(request, row):
            return HttpResponseForbidden("forbidden")

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
            new_ids = list(ids)
        elif op == "clear":
            new_ids = []
        else:
            return HttpResponseBadRequest("op must be one of add|remove|replace|clear")

        data["ids"] = new_ids
        row.data = cast(Any, data)
        row.save(update_fields=["data"])
        return JsonResponse({"ok": True, "id": row.id, "count": len(new_ids)})

    def get(self, request, model: Optional[str] = None, ident: Optional[str] = None, *args, **kwargs):
        model_slug_val = (model or kwargs.get("model"))
        if not isinstance(model_slug_val, str) or not model_slug_val:
            return HttpResponseBadRequest("model required")
        model_slug = cast(str, model_slug_val)

        ident_val = ident or kwargs.get("ident")
        if ident_val is None or (isinstance(ident_val, str) and not ident_val.strip()):
            return HttpResponseBadRequest("ident required")
        ident_str = str(ident_val)

        row = self._load_saved_set_setting(request, model_slug, ident_str)
        model_cls = self._model_class(model_slug)

        data_dict = getattr(row, "data", {}) or {}
        ids = list(data_dict.get("ids") or [])
        if ids:
            qs = model_cls._default_manager.filter(pk__in=ids)
        else:
            qs = model_cls._default_manager.none()

        def _serialize(o):
            try:
                return self.serialize_with_view_allowlist(o, request=request, ctx="list")
            except Exception:
                return model_to_dict(o)

        data = [_serialize(o) for o in qs]
        return JsonResponse({"ok": True, "data": data, "meta": {"count": len(data)}})

    def delete(self, request, model: Optional[str] = None, ident: Optional[str] = None, *args, **kwargs):
        try:
            from apps.core.models import Setting
        except Exception:
            return HttpResponseBadRequest("Setting model unavailable")

        model_slug_val = (model or kwargs.get("model"))
        if not isinstance(model_slug_val, str) or not model_slug_val:
            return HttpResponseBadRequest("model required")
        model_slug = cast(str, model_slug_val)

        ident_val = ident or kwargs.get("ident")
        if ident_val is None or (isinstance(ident_val, str) and not ident_val.strip()):
            return HttpResponseBadRequest("ident required")
        ident_str = str(ident_val)

        row = self._load_saved_set_setting(request, model_slug, ident_str)
        if not self._can_access_saved_setting(request, row):
            return HttpResponseForbidden("forbidden")
        row.delete()
        return JsonResponse({"ok": True, "deleted": True})