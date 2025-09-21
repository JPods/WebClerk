from __future__ import annotations
from typing import Any, Dict, List, Optional
from django.forms.models import model_to_dict
from django.db.models import QuerySet, Model
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from apps.core.wcapi import registry

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
    # TODO: enforce role/tenant/publish/reserved with Settings
    return qs

class WCAPIGetView(APIView):
    http_method_names = ["post", "options", "head"]

    def post(self, request, *args, **kwargs):
        body: Dict[str, Any] = request.data or {}
        model_key = body.get("model")
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
            data = to_dict(obj)
            if fields:
                data = {k: data.get(k) for k in fields}
            return Response({"item": data}, status=status.HTTP_200_OK)

        if isinstance(filters, dict) and filters:
            qs = qs.filter(**filters)

        items: List[Dict[str, Any]] = []
        for obj in qs[:500]:
            data = to_dict(obj)
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
        model_key = body.get("model")
        record_id = body.get("id")
        data = body.get("data") or {}

        ModelCls = registry.resolve(model_key or "")
        if not ModelCls or not isinstance(data, dict):
            return Response({"detail": "invalid payload"}, status=status.HTTP_400_BAD_REQUEST)

        clean = filter_input_fields(ModelCls, data)

        if record_id:
            try:
                obj = ModelCls.objects.get(pk=record_id)
            except ModelCls.DoesNotExist:  # type: ignore[attr-defined]
                return Response({"detail": "not found"}, status=status.HTTP_404_NOT_FOUND)
            for k, v in clean.items():
                setattr(obj, k, v)
            obj.save()
            return Response({"id": obj.pk, "action": "updated"}, status=status.HTTP_200_OK)

        obj = ModelCls.objects.create(**clean)
        return Response({"id": obj.pk, "action": "created"}, status=status.HTTP_201_CREATED)

class WCAPIDeleteView(APIView):
    http_method_names = ["post", "options", "head"]

    def post(self, request, *args, **kwargs):
        body: Dict[str, Any] = request.data or {}
        model_key = body.get("model")
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
        return Response({"detail": "not implemented"}, status=status.HTTP_501_NOT_IMPLEMENTED)