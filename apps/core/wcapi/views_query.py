from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.http import Http404
from typing import Any, Optional, cast
from django.forms.models import model_to_dict

from apps.core.wcapi.mixins import SettingsDrivenCRUDMixin
from apps.core.wcapi.utils import parse_json_body, coerce_query_payload, resolve_model_slug


class RESTOpenQueryView(SettingsDrivenCRUDMixin, APIView):
    http_method_names = ["post", "options", "head"]

    def _model_class(self, model_slug: str):
        try:
            return resolve_model_slug(model_slug)
        except Exception as e:
            raise Http404(str(e))

    def post(self, request, model: Optional[str] = None, *args, **kwargs):
        action = kwargs.get("action")
        model_value = model if model is not None else kwargs.get("model")
        if not model_value:
            raise Http404("Missing model")
        model_slug = str(model_value)
        model_cls = self._model_class(model_slug)

        if action == "save":
            raw_body = parse_json_body(request)
            if not isinstance(raw_body, dict):
                payload = {'status': 'fail', 'code': 400, 'ok': False, 'message': 'request body must be a JSON object', 'data': None}
                return Response(payload, status=status.HTTP_400_BAD_REQUEST)
            body = coerce_query_payload(raw_body)
            name = body.get("name")
            dsl = body.get("dsl") or {}
            scope = body.get("scope") or {}
            labels = body.get("labels") or []
            comment = body.get("comment") or ""
            if not name or not isinstance(dsl, dict) or not isinstance(scope, dict):
                payload = {'status': 'fail', 'code': 400, 'ok': False, 'message': 'name, dsl, scope required', 'data': None}
                return Response(payload, status=status.HTTP_400_BAD_REQUEST)

            owner_id = getattr(getattr(request, "user", None), "id", None)
            from apps.core.models import Setting
            row = Setting.objects.create(
                is_active=True,
                name=name,
                purpose="saved_query",
                role=scope.get("type", "all"),
                model_name=model_slug,
                data={"dsl": dsl, "scope": scope, "labels": labels, "owner_id": owner_id, "comment": comment},
            )
            payload = {'status': 'success', 'code': 200, 'ok': True, 'id': row.id, 'name': row.name}
            return Response(payload, status=status.HTTP_200_OK)

        # Run open query (optionally from saved)
        _, _, _, meta = self.get_view_edit_allowlists(model_cls, request=request, ctx="list")
        body = parse_json_body(request)
        if not isinstance(body, dict):
            body = {}
        saved_ident = str(body.get("saved") or request.GET.get("saved") or "").strip()
        if saved_ident:
            try:
                row = self._load_saved_query_setting(request, model_slug, saved_ident)
                body = (getattr(row, "data", {}) or {}).get("dsl") or {}
            except Exception:
                payload = {'status': 'fail', 'code': 404, 'ok': False, 'message': 'saved query not found', 'data': []}
                return Response(payload, status=status.HTTP_404_NOT_FOUND)
        qs, paging = self.evaluate_open_query(model_cls, request, meta)
        qs = self.filter_by_saved_set(qs, request, model_cls, meta)
        serializer = getattr(self, "serialize_with_view_allowlist", None)
        if callable(serializer):
            data = [serializer(o, request=request, ctx="list") for o in qs]
        else:
            data = [model_to_dict(o) for o in qs]
        payload = {'status': 'success', 'code': 200, 'ok': True, 'data': data, 'items': data, 'meta': paging}
        return Response(payload, status=status.HTTP_200_OK)


class RESTSavedSetView(SettingsDrivenCRUDMixin, APIView):
    http_method_names = ["post", "patch", "get", "delete", "options", "head"]

    def _model_class(self, model_slug: str):
        try:
            return resolve_model_slug(model_slug)
        except Exception as e:
            raise Http404(str(e))

    def apply_role_scope(self, qs, request, meta, roles):
        impl = getattr(SettingsDrivenCRUDMixin, "apply_role_scope", None)
        if callable(impl):
            return impl(self, qs, request, meta, roles)
        return qs

    def post(self, request, model: Optional[str] = None, *args, **kwargs):
        from apps.core.models import Setting
        model_slug = model or kwargs.get("model")
        if not model_slug:
            raise Http404("Missing model")
        body = parse_json_body(request)
        if not isinstance(body, dict):
            payload = {'status': 'fail', 'code': 400, 'ok': False, 'message': 'request body must be a JSON object', 'data': None}
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)
        name = (str(body.get("name") or "")).strip()
        ids = list(body.get("ids") or [])
        scope = body.get("scope") or {}
        labels = body.get("labels") or []
        comment = body.get("comment") or ""
        if not name or not isinstance(ids, list) or not isinstance(scope, dict):
            payload = {'status': 'fail', 'code': 400, 'ok': False, 'message': 'name, ids, scope required', 'data': None}
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)
        owner_id = getattr(getattr(request, "user", None), "id", None)
        row = Setting.objects.create(
            is_active=True,
            name=name,
            purpose="saved_set",
            role=scope.get("type", "all"),
            model_name=model_slug,
            data={"ids": ids, "scope": scope, "labels": labels, "owner_id": owner_id, "comment": comment},
        )
        payload = {'status': 'success', 'code': 200, 'ok': True, 'id': row.id, 'name': row.name, 'count': len(ids)}
        return Response(payload, status=status.HTTP_200_OK)

    def patch(self, request, model: Optional[str] = None, ident: Optional[str] = None, *args, **kwargs):
        model_slug = model or kwargs.get("model")
        if not model_slug:
            raise Http404("Missing model")
        ident_value = ident if ident is not None else kwargs.get("ident")
        row = self._load_saved_set_setting(request, model_slug, str(ident_value))
        if not self._can_access_saved_setting(request, row):
            payload = {'status': 'fail', 'code': 403, 'ok': False, 'message': 'forbidden', 'data': None}
            return Response(payload, status=status.HTTP_403_FORBIDDEN)

        body = parse_json_body(request)
        if not isinstance(body, dict):
            payload = {'status': 'fail', 'code': 400, 'ok': False, 'message': 'request body must be a JSON object', 'data': None}
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)
        op = (str(body.get("op") or "")).lower()
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
            payload = {'status': 'fail', 'code': 400, 'ok': False, 'message': 'op must be add|remove|replace|clear', 'data': None}
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)

        data["ids"] = new_ids
        row.data = cast(Any, data)
        row.save(update_fields=["data"])
        payload = {'status': 'success', 'code': 200, 'ok': True, 'data': {'ids': new_ids, 'count': len(new_ids)}}
        return Response(payload, status=status.HTTP_200_OK)

    def get(self, request, model: Optional[str] = None, ident: Optional[str] = None, *args, **kwargs):
        model_val = model if model is not None else kwargs.get("model")
        if not model_val:
            raise Http404("Missing model")
        model_slug = str(model_val)
        ident_value = ident if ident is not None else kwargs.get("ident")
        if not ident_value:
            raise Http404("Missing ident")
        # Load saved set
        row = self._load_saved_set_setting(request, model_slug, str(ident_value))
        if not self._can_access_saved_setting(request, row):
            payload = {'status': 'fail', 'code': 403, 'ok': False, 'message': 'forbidden', 'data': None}
            return Response(payload, status=status.HTTP_403_FORBIDDEN)
        data_payload = getattr(row, "data", {}) or {}
        ids = list(data_payload.get("ids") or [])
        # Build queryset and apply role scope
        model_cls = self._model_class(model_slug)
        qs = model_cls.objects.all()
        _, _, _, meta = self.get_view_edit_allowlists(model_cls, request=request, ctx="list")
        qs = cast(Any, self.apply_role_scope(qs, request, meta, self._roles_for(request)))
        qs = qs.filter(pk__in=ids) if ids else qs.none()
        serializer = getattr(self, "serialize_with_view_allowlist", None)
        if callable(serializer):
            data = [serializer(o, request=request, ctx="list") for o in qs]
        else:
            data = [model_to_dict(o) for o in qs]
        payload = {'status': 'success', 'code': 200, 'ok': True, 'data': data, 'meta': {'count': len(data)}}
        return Response(payload, status=status.HTTP_200_OK)
    def delete(self, request, model: Optional[str] = None, ident: Optional[str] = None, *args, **kwargs):
        model_slug = model or kwargs.get("model")
        if not model_slug:
            raise Http404("Missing model")
        ident_value = ident if ident is not None else kwargs.get("ident")
        row = self._load_saved_set_setting(request, model_slug, str(ident_value))
        if not self._can_access_saved_setting(request, row):
            payload = {'status': 'fail', 'code': 403, 'ok': False, 'message': 'forbidden', 'data': None}
            return Response(payload, status=status.HTTP_403_FORBIDDEN)
        row.delete()
        payload = {'status': 'success', 'code': 200, 'ok': True, 'deleted': True}
        return Response(payload, status=status.HTTP_200_OK)