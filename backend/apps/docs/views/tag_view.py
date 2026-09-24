from __future__ import annotations
from apps.core.services.door import Actor
from typing import Any, Optional, List
from apps.docs.models import Tag
from django.forms.models import model_to_dict

from apps.core.services.field_projection import filter_response_data
from apps.core.services.role_filter import get_allowed_fields, inject_role_filters
from apps.core.utils.hierarchy import parent_field_name, children_qs, parent_chain
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
class TagHierarchyView(APIView):

    """
    Tag hierarchy endpoint (custom; standard CRUD is via wcapi).
    Returns item + parents + children; POST links/unlinks child via the Tag parent FK.
    """
    model = Tag
    model_key = "tag"
    http_method_names = ["get", "post", "options", "head"]

    def _visible(self, request):
        return self.model.objects.filter(inject_role_filters(Actor.from_request(request), self.model_key))

    def _project(self, request, obj) -> dict:
        return filter_response_data(Actor.from_request(request), self.model_key, model_to_dict(obj))

    def get(self, request, pk: int):
        obj = self._visible(request).filter(pk=pk).first()
        if obj is None:
            return Response({"detail": "not found"}, status=status.HTTP_404_NOT_FOUND)

        visible_ids = set(self._visible(request).values_list("pk", flat=True))
        pf = parent_field_name(self.model)
        item = self._project(request, obj)
        children = [self._project(request, c) for c in children_qs(self.model, obj, pf)
                    if c.pk in visible_ids]
        parents = [self._project(request, p) for p in parent_chain(self.model, obj, pf=pf)
                   if p.pk in visible_ids]

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

        # The parent link is an edit of the child's parent field: it must be on
        # this role's edit list for tag (positive list, access.py).
        parent_leaf = self.model._meta.get_field(pf).attname
        if parent_leaf not in get_allowed_fields(Actor.from_request(request), self.model_key, mode="edit"):
            return Response({"detail": "forbidden"}, status=status.HTTP_403_FORBIDDEN)

        parent = self._visible(request).filter(pk=pk).first()
        if parent is None:
            return Response({"detail": "not found"}, status=status.HTTP_404_NOT_FOUND)

        data = getattr(request, "data", {}) or {}
        child_id = data.get("child_id") or data.get("child") or data.get("id") or data.get("tag_id")
        if not child_id:
            return Response({"detail": "missing child id"}, status=status.HTTP_400_BAD_REQUEST)

        child = self._visible(request).filter(pk=child_id).first()
        if child is None:
            return Response({"detail": "invalid child"}, status=status.HTTP_400_BAD_REQUEST)

        # Link or unlink
        if str(data.get("detach") or data.get("remove") or "").strip().lower() in {"1", "true", "t", "yes", "y"}:
            setattr(child, pf, None)
        else:
            setattr(child, pf, parent)

        child.save(update_fields=[pf])

        return Response({"ok": True, "parent_id": getattr(parent, "id", None), "child_id": getattr(child, "id", None)}, status=status.HTTP_200_OK)
