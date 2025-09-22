from __future__ import annotations
from typing import Any, Dict, List, Optional, Type

from django.db.models import Model
from django.db.models.fields.reverse_related import ManyToOneRel
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from apps.core.wcapi import services, policy


def parent_field_name(model: Type[Model]) -> Optional[str]:
    # Prefer conventional "parent" FK if present
    try:
        f = model._meta.get_field("parent")
        if getattr(f, "many_to_one", False) and getattr(f, "related_model", None) is model:
            return "parent"
    except Exception:
        pass
    # Discover a self-referential FK (exclude auto-created reverse rels)
    for f in model._meta.get_fields():
        try:
            if getattr(f, "many_to_one", False) and getattr(f, "related_model", None) is model and not getattr(f, "auto_created", False):
                return f.name
        except Exception:
            continue
    return None

def children_qs(model: Type[Model], obj: Model, parent_field: Optional[str] = None):
    pf = parent_field or parent_field_name(model)

    # Prefer reverse relation whose remote field name matches the parent field
    for f in model._meta.get_fields():
        try:
            if isinstance(f, ManyToOneRel) and getattr(f, "related_model", None) is model:
                remote = getattr(f, "remote_field", None)
                if pf and remote and getattr(remote, "name", None) == pf:
                    accessor = f.get_accessor_name()
                    if accessor:
                        manager = getattr(obj, accessor)
                        return manager.all()
        except Exception:
            continue

    # Fallback to any reverse relation to the same model
    for f in model._meta.get_fields():
        try:
            if isinstance(f, ManyToOneRel) and getattr(f, "related_model", None) is model:
                accessor = f.get_accessor_name()
                if accessor:
                    manager = getattr(obj, accessor)
                    return manager.all()
        except Exception:
            continue

    return model.objects.none()


def parent_chain(model: Type[Model], obj: Model, max_depth: int = 10, pf: Optional[str] = None) -> List[Model]:
    field = pf or parent_field_name(model)
    chain: List[Model] = []
    if not field:
        return chain
    current = obj
    for _ in range(max_depth):
        parent = getattr(current, field, None)
        if not parent:
            break
        chain.append(parent)
        current = parent
    return chain


class GenericHierarchyView(APIView):
    """
    Generic GET/POST hierarchy view.
    Subclass and set `model` to your Django model class.
    """
    model: Optional[Type[Model]] = None  # override in subclass
    http_method_names = ["get", "post", "options", "head"]

    def _truthy(self, v: Any) -> bool:
        return str(v).strip().lower() in {"1", "true", "t", "yes", "y"}

    def get(self, request, pk: int):
        model = self.model
        if model is None:
            return Response({"detail": "model not configured"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        try:
            obj = model.objects.get(pk=pk)
        except model.DoesNotExist:
            return Response({"detail": "not found"}, status=status.HTTP_404_NOT_FOUND)

        pf = parent_field_name(model)
        allow = policy.field_allowlist(model, request=request)

        data_item = services.to_dict(obj, allow=allow)
        kids = children_qs(model, obj, pf)
        kids_payload = [services.to_dict(c, allow=allow) for c in kids]
        parents_payload = [services.to_dict(p, allow=allow) for p in parent_chain(model, obj, pf=pf)]

        return Response(
            {"item": data_item, "parents": parents_payload, "children": kids_payload, "count_children": len(kids_payload)},
            status=status.HTTP_200_OK,
        )
    def post(self, request, pk: int):
        model = self.model
        if model is None:
            return Response({"detail": "model not configured"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        pf = parent_field_name(model)
        if not pf:
            return Response({"detail": "hierarchy unsupported"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            parent = model.objects.get(pk=pk)
        except model.DoesNotExist:
            return Response({"detail": "not found"}, status=status.HTTP_404_NOT_FOUND)

        body = getattr(request, "data", {}) or {}
        child_id = body.get("child_id") or body.get("child") or body.get("id") or body.get("tag_id")
        if not child_id:
            return Response({"detail": "missing child id"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            child = model.objects.get(pk=child_id)
        except model.DoesNotExist:
            return Response({"detail": "invalid child"}, status=status.HTTP_400_BAD_REQUEST)

        if self._truthy(body.get("detach") or body.get("remove")):
            setattr(child, pf, None)
        else:
            setattr(child, pf, parent)

        try:
            child.save(update_fields=[pf])
        except Exception:
            child.save()

        return Response({"ok": True, "parent_id": getattr(parent, "id", None), "child_id": getattr(child, "id", None)}, status=status.HTTP_200_OK)
        