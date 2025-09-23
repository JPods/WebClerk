from typing import Any, Type
from rest_framework import mixins, viewsets, permissions, filters
from rest_framework.response import Response
from rest_framework.request import Request

from .mixins import RegistryQuerysetMixin, QSearchMixin, DevFallbackMetaMixin
from .serializers import make_model_serializer

class WCAPIModelViewSet(
    RegistryQuerysetMixin,
    QSearchMixin,
    DevFallbackMetaMixin,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    model_key: str
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering = ["-id"]

    def get_serializer_class(self) -> Type[Any]:
        cfg = self.get_registry_config()
        if self.action in ("retrieve", "update", "partial_update") and cfg.detail_serializer:
            return cfg.detail_serializer  # type: ignore[return-value]
        if cfg.list_serializer:
            return cfg.list_serializer  # type: ignore[return-value]
        return make_model_serializer(cfg.model)

    def get_permissions(self):
        cfg = self.get_registry_config()
        if cfg.permission_classes:
            return [p() for p in cfg.permission_classes]  # type: ignore[misc]
        return super().get_permissions()

    def list(self, request: Request, *args, **kwargs):
        cfg = self.get_registry_config()
        qs = self.apply_q_search(self.filter_queryset(self.get_queryset()), request)
        ordering = list(getattr(self, "ordering", None) or []) or list(cfg.ordering or [])
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