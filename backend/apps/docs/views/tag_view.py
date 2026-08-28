from __future__ import annotations
from typing import Any, Optional, List
from apps.docs.models import Tag
from apps.core.utils.mixins import SettingsDrivenCRUDMixin
from apps.core.utils.hierarchy import parent_field_name, children_qs, parent_chain
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
class TagHierarchyView(SettingsDrivenCRUDMixin, APIView):

    """
    Tag hierarchy endpoint (custom; standard CRUD is via wcapi).
    Returns item + parents + children; POST links/unlinks child via the Tag parent FK.
    """
    model = Tag
    http_method_names = ["get", "post", "options", "head"]

    def get(self, request, pk: int):
        try:
            obj = self.model.objects.get(pk=pk)
        except self.model.DoesNotExist:
            return Response({"detail": "not found"}, status=status.HTTP_404_NOT_FOUND)

        item = self.serialize_with_view_allowlist(obj, request=request, ctx="display")
        pf = parent_field_name(self.model)
        kids = children_qs(self.model, obj, pf)
        children = [self.serialize_with_view_allowlist(c, request=request, ctx="list") for c in kids]
        parents = [self.serialize_with_view_allowlist(p, request=request, ctx="list") for p in parent_chain(self.model, obj, pf=pf)]

        return Response({"item": item, "parents": parents, "children": children, "count_children": len(children)})

    def post(self, request, pk: int):
        """
        Body:
          { child_id|child|id|tag_id: <int>, detach|remove: true|false }
        Security:
          - Edit must be allowed on the parent FK field for this role; else 403.
        """
        pf = parent_field_name(self.model)
        if not pf:
            return Response({"detail": "hierarchy unsupported"}, status=status.HTTP_400_BAD_REQUEST)

        # Enforce edit permission on the parent field via settings
        _, edit_fields, _, _meta = self.get_view_edit_allowlists(self.model, request=request, ctx="display")
        if edit_fields is not None and pf not in edit_fields:
            return Response({"detail": "forbidden"}, status=status.HTTP_403_FORBIDDEN)

        try:
            parent = self.model.objects.get(pk=pk)
        except self.model.DoesNotExist:
            return Response({"detail": "not found"}, status=status.HTTP_404_NOT_FOUND)

        data = getattr(request, "data", {}) or {}
        child_id = data.get("child_id") or data.get("child") or data.get("id") or data.get("tag_id")
        if not child_id:
            return Response({"detail": "missing child id"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            child = self.model.objects.get(pk=child_id)
        except self.model.DoesNotExist:
            return Response({"detail": "invalid child"}, status=status.HTTP_400_BAD_REQUEST)

        # Link or unlink
        if str(data.get("detach") or data.get("remove") or "").strip().lower() in {"1", "true", "t", "yes", "y"}:
            setattr(child, pf, None)
        else:
            setattr(child, pf, parent)

        try:
            child.save(update_fields=[pf])
        except Exception:
            child.save()

        return Response({"ok": True, "parent_id": getattr(parent, "id", None), "child_id": getattr(child, "id", None)}, status=status.HTTP_200_OK)
