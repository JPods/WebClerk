from typing import Any, Type
from rest_framework import viewsets, permissions, filters, status
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.decorators import action

from .mixins import (
    RegistryQuerysetMixin,
    QSearchMixin,
    DevFallbackMetaMixin,
    SettingsDrivenCRUDMixin,
)
from .serializers import make_model_serializer

class WCAPIModelViewSet(
    RegistryQuerysetMixin,
    QSearchMixin,
    DevFallbackMetaMixin,
    SettingsDrivenCRUDMixin,   # enables evaluate_open_query and helpers
    viewsets.ModelViewSet,
):
    model_key: str
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering = ["-id"]

    def get_serializer_class(self) -> Type[Any]:
        cfg = self.get_registry_config()
        if self.action in ("retrieve", "update", "partial_update") and getattr(cfg, "detail_serializer", None):
            return cfg.detail_serializer  # type: ignore[return-value]
        if getattr(cfg, "list_serializer", None):
            return cfg.list_serializer  # type: ignore[return-value]
        return make_model_serializer(cfg.model)

    def get_permissions(self):
        cfg = self.get_registry_config()
        if getattr(cfg, "permission_classes", None):
            return [p() for p in cfg.permission_classes]  # type: ignore[misc]
        return super().get_permissions()

    def list(self, request: Request, *args, **kwargs):
        cfg = self.get_registry_config()
        qs = self.apply_q_search(self.filter_queryset(self.get_queryset()), request)
        ordering = list(getattr(self, "ordering", None) or []) or list(getattr(cfg, "ordering", []) or [])
        if ordering:
            try:
                qs = qs.order_by(*ordering)
            except Exception:
                pass
        page = self.paginate_queryset(qs)
        if page is not None:
            ser = self.get_serializer(page, many=True)
            items = ser.data
            try:
                page_num = getattr(self.paginator.page, "number", 1)  # type: ignore[attr-defined]
                page_size = self.paginator.get_page_size(request)     # type: ignore[attr-defined]
                total = qs.count()
            except Exception:
                page_num, page_size, total = 1, len(items), qs.count()
            meta = {"page": page_num, "page_size": page_size, "count": total}
            self.add_dev_fallback_meta(meta)
            return Response({"items": items, "meta": meta, "ok": True})
        ser = self.get_serializer(qs, many=True)
        items = ser.data
        meta = {"page": 1, "page_size": len(items), "count": qs.count()}
        self.add_dev_fallback_meta(meta)
        return Response({"items": items, "meta": meta, "ok": True})

    @action(detail=False, methods=["post"])
    def query(self, request: Request):
        """
        Open query endpoint: POST /<model-key>/query
        Body example:
          {
            "where": [{"field":"name", "op":"icontains", "value":"foo"}],
            "order_by": ["-id"],
            "limit": 50,
            "offset": 0
          }
        """
        cfg = self.get_registry_config()
        # Build minimal meta to drive policy (dev-fallback ok)
        _, _, _, meta = self.get_view_edit_allowlists(cfg.model, request=request, ctx=None)
        qs, qmeta = self.evaluate_open_query(cfg.model, request, meta)
        page = self.paginate_queryset(qs)
        ser = self.get_serializer(page if page is not None else qs, many=True)
        items = ser.data
        out_meta = {"count": qs.count(), **qmeta}
        if page is not None:
            try:
                out_meta.update({
                    "page": getattr(self.paginator.page, "number", 1),  # type: ignore[attr-defined]
                    "page_size": self.paginator.get_page_size(request), # type: ignore[attr-defined]
                })
            except Exception:
                out_meta.setdefault("page", 1)
                out_meta.setdefault("page_size", len(items))
        self.add_dev_fallback_meta(out_meta)
        return Response({"items": items, "meta": out_meta, "ok": True}, status=status.HTTP_200_OK)