from __future__ import annotations
from typing import Any, List, Optional, cast

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from apps.core.wcapi import services, policy
from apps.docs.models import Tag


class TagHierarchyView(APIView):
    """
    GET  /tag/<pk>/hierarchy
      -> { item, parents[], children[], count_children }
    POST /tag/<pk>/hierarchy
      -> attach/detach child to this parent
         body: { child_id|child|id|tag_id, detach|remove: 1/true (optional) }
    """
    http_method_names = ["get", "post", "options", "head"]

    def _truthy(self, v: Any) -> bool:
        return str(v).strip().lower() in {"1", "true", "t", "yes", "y"}

    def _parent_field_name(self) -> Optional[str]:
        # Prefer a conventional "parent" FK if present
        if hasattr(Tag, "parent"):
            return "parent"
        # Discover a self-referential FK to Tag (not auto-created reverse)
        for f in Tag._meta.get_fields():
            try:
                if getattr(f, "many_to_one", False) and getattr(f, "related_model", None) is Tag and not getattr(f, "auto_created", False):
                    return f.name
            except Exception:
                continue
        return None

    def _children_qs(self, obj: Tag):
        # Use reverse accessor tied to the chosen parent field when possible
        parent_field = self._parent_field_name()
        if parent_field:
            for f in Tag._meta.get_fields():
                try:
                    if getattr(f, "one_to_many", False) and getattr(f, "related_model", None) is Tag:
                        remote = getattr(f, "remote_field", None)
                        if remote and getattr(remote, "name", None) == parent_field:
                            get_accessor = getattr(f, "get_accessor_name", None)
                            if callable(get_accessor):
                                accessor = cast(str, get_accessor())
                                return getattr(obj, accessor).all()
                except Exception:
                    continue
        # Fallback to any auto-created reverse one-to-many
        for f in Tag._meta.get_fields():
            try:
                if getattr(f, "one_to_many", False) and getattr(f, "related_model", None) is Tag:
                    get_accessor = getattr(f, "get_accessor_name", None)
                    if callable(get_accessor):
                        accessor = cast(str, get_accessor())
                        return getattr(obj, accessor).all()
            except Exception:
                continue
        return Tag.objects.none()

    def get(self, request, pk: int):
        try:
            obj = Tag.objects.get(pk=pk)
        except Tag.DoesNotExist:
            return Response({"detail": "not found"}, status=status.HTTP_404_NOT_FOUND)

        allow = policy.field_allowlist(Tag, request=request)
        item = services.to_dict(obj, allow=allow)

        children_qs = self._children_qs(obj)
        child_allow = policy.field_allowlist(Tag, request=request)
        children = [services.to_dict(c, allow=child_allow) for c in children_qs]

        parents: List[dict] = []
        parent_field = self._parent_field_name()
        if parent_field:
            current = obj
            for _ in range(10):  # guard against cycles
                parent = getattr(current, parent_field, None)
                if not parent:
                    break
                parents.append(services.to_dict(parent, allow=allow))
                current = parent

        return Response(
            {"item": item, "parents": parents, "children": children, "count_children": len(children)},
            status=status.HTTP_200_OK,
        )

    def post(self, request, pk: int):
        parent_field = self._parent_field_name()
        if not parent_field:
            return Response({"detail": "hierarchy unsupported"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            parent = Tag.objects.get(pk=pk)
        except Tag.DoesNotExist:
            return Response({"detail": "not found"}, status=status.HTTP_404_NOT_FOUND)

        body = getattr(request, "data", {}) or {}
        child_id = body.get("child_id") or body.get("child") or body.get("id") or body.get("tag_id")
        if not child_id:
            return Response({"detail": "missing child id"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            child = Tag.objects.get(pk=child_id)
        except Tag.DoesNotExist:
            return Response({"detail": "invalid child"}, status=status.HTTP_400_BAD_REQUEST)

        if self._truthy(body.get("detach") or body.get("remove")):
            setattr(child, parent_field, None)
        else:
            setattr(child, parent_field, parent)

        try:
            child.save(update_fields=[parent_field])
        except Exception:
            child.save()

        return Response({"ok": True, "parent_id": parent.id, "child_id": child.id}, status=status.HTTP_200_OK)