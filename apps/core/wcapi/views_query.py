from django.http import JsonResponse, HttpResponseBadRequest, Http404, HttpResponseForbidden
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from django.views import View
from django.forms.models import model_to_dict
from apps.core.wcapi.mixins import SettingsDrivenCRUDMixin
from typing import Optional, cast, Any

class RESTOpenQueryView(SettingsDrivenCRUDMixin, APIView):
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

    def post(self, request, model: Optional[str] = None, *args, **kwargs):
        action = kwargs.get("action")
        model_slug = model if isinstance(model, str) else kwargs.get("model")
        if not isinstance(model_slug, str) or not model_slug.strip():
            return Response({"detail": "model required"}, status=status.HTTP_400_BAD_REQUEST)
        model_cls = self._model_class(model_slug)

        if action == "save":
            body = self._json_body(request)
            name = (body.get("name") or "").strip()
            dsl = body.get("dsl") or {}
            scope = body.get("scope") or {}
            labels = body.get("labels") or []
            comment = body.get("comment") or ""
            if not name or not isinstance(dsl, dict) or not isinstance(scope, dict):
                return Response({"detail": "name, dsl, scope required"}, status=status.HTTP_400_BAD_REQUEST)
            from apps.core.models import Setting
            owner_id = getattr(getattr(request, "user", None), "id", None)
            row = Setting.objects.create(
                is_active=True,
                name=name,
                purpose="saved_query",
                role=scope.get("type", "all"),
                model_name=model_slug,
                data={"dsl": dsl, "scope": scope, "labels": labels, "owner_id": owner_id},
                comment=comment,
            )
            return Response({"ok": True, "id": row.id, "name": row.name}, status=status.HTTP_200_OK)

        # run query (optionally from saved)
        view_fields, _, _, meta = self.get_view_edit_allowlists(model_cls, request=request, ctx="list")
        body = self._json_body(request)
        saved_ident = (body.get("saved") or request.GET.get("saved") or "").strip()
        if saved_ident:
            try:
                row = self._load_saved_query_setting(request, model_slug, saved_ident)
                body = (getattr(row, "data", {}) or {}).get("dsl") or {}
            except Exception:
                return Response({"ok": True, "data": [], "items": [], "meta": {"error": "saved query not found"}}, status=404)

        qs, paging = self.evaluate_open_query(model_cls, request, meta)
        qs = self.filter_by_saved_set(qs, request, model_cls, meta)
        data = [self.serialize_with_view_allowlist(o, request=request, ctx="list") for o in qs]
        return Response({"ok": True, "data": data, "items": data, "meta": paging}, status=status.HTTP_200_OK)


class RESTSavedSetView(SettingsDrivenCRUDMixin, APIView):
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

    def post(self, request, model: Optional[str] = None, *args, **kwargs):
        from apps.core.models import Setting
        model_slug = model if isinstance(model, str) else kwargs.get("model")
        if not isinstance(model_slug, str) or not model_slug.strip():
            return Response({"detail": "model required"}, status=status.HTTP_400_BAD_REQUEST)
        body = self._json_body(request)
        name = (body.get("name") or "").strip()
        ids = list(body.get("ids") or [])
        scope = body.get("scope") or {}
        labels = body.get("labels") or []
        comment = body.get("comment") or ""
        if not name or not isinstance(ids, list) or not isinstance(scope, dict):
            return Response({"detail": "name, ids, scope required"}, status=status.HTTP_400_BAD_REQUEST)
        owner_id = getattr(getattr(request, "user", None), "id", None)
        row = Setting.objects.create(
            is_active=True,
            name=name,
            purpose="saved_set",
            role=scope.get("type", "all"),
            model_name=model_slug,
            data={"ids": ids, "scope": scope, "labels": labels, "owner_id": owner_id},
            comment=comment,
        )
        return Response({"ok": True, "id": row.id, "name": row.name}, status=status.HTTP_200_OK)

    def patch(self, request, model: Optional[str] = None, ident: Optional[str] = None, *args, **kwargs):
        model_slug = model if isinstance(model, str) else kwargs.get("model")
        if not isinstance(model_slug, str) or not model_slug.strip():
            return Response({"detail": "model required"}, status=status.HTTP_400_BAD_REQUEST)
        ident_val = ident if ident is not None else kwargs.get("ident")
        if not isinstance(ident_val, str) or not ident_val.strip():
            return Response({"detail": "ident required"}, status=status.HTTP_400_BAD_REQUEST)
        row = self._load_saved_set_setting(request, model_slug, ident_val)
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
        row.data = data
        row.save(update_fields=["data"])
        return Response({"ok": True, "ids": new_ids}, status=status.HTTP_200_OK)

    def get(self, request, model: Optional[str] = None, ident: Optional[str] = None, *args, **kwargs):
        model_slug = model if isinstance(model, str) else kwargs.get("model")
        if not isinstance(model_slug, str) or not model_slug.strip():
            return Response({"detail": "model required"}, status=status.HTTP_400_BAD_REQUEST)
        ident_val = ident if ident is not None else kwargs.get("ident")
        if not isinstance(ident_val, str) or not ident_val.strip():
            return Response({"detail": "ident required"}, status=status.HTTP_400_BAD_REQUEST)
        row = self._load_saved_set_setting(request, model_slug, ident_val)
        model_cls = self._model_class(model_slug)
        view_fields, _, _, meta = self.get_view_edit_allowlists(model_cls, request=request, ctx="list")
        ids = list(((getattr(row, "data", {}) or {}).get("ids") or []))
        qs = self.base_queryset(model_cls)
        qs = self.apply_role_scope(qs, request, meta, self._roles_for(request))
        if ids:
            qs = qs.filter(id__in=ids)
        data = [self.serialize_with_view_allowlist(o, request=request, ctx="list") for o in qs]
        return Response({"ok": True, "data": data, "items": data, "count": len(data)}, status=status.HTTP_200_OK)

    def delete(self, request, model: Optional[str] = None, ident: Optional[str] = None, *args, **kwargs):
        model_slug = model if isinstance(model, str) else kwargs.get("model")
        if not isinstance(model_slug, str) or not model_slug.strip():
            return Response({"detail": "model required"}, status=status.HTTP_400_BAD_REQUEST)
        ident_val = ident if ident is not None else kwargs.get("ident")
        if not isinstance(ident_val, str) or not ident_val.strip():
            return Response({"detail": "ident required"}, status=status.HTTP_400_BAD_REQUEST)
        row = self._load_saved_set_setting(request, model_slug, ident_val)
        if not self._can_access_saved_setting(request, row):
            return Response({"detail": "forbidden"}, status=status.HTTP_403_FORBIDDEN)
        row.delete()
        return Response({"ok": True, "deleted": True}, status=status.HTTP_200_OK)