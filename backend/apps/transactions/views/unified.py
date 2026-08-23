from typing import Tuple, Type, Optional, Any, Dict, List
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import generics, response, status, views
from django.apps import apps

# Prefer project helpers; fall back to DRF if not available or invalid
try:
    from apps.core.views import BaseJSONAPIView as _ProjectBaseJSONAPIView, api_response  # type: ignore
except ImportError:
    _ProjectBaseJSONAPIView = None  # type: ignore
    api_response = None  # type: ignore

if _ProjectBaseJSONAPIView is not None and isinstance(_ProjectBaseJSONAPIView, type):
    BaseJSONAPIView = _ProjectBaseJSONAPIView
else:
    from rest_framework.views import APIView as BaseJSONAPIView
    # Only define a fallback api_response if not provided by project helpers
    if 'api_response' not in globals() or not callable(api_response):  # type: ignore[name-defined]
        from rest_framework import response as _drf_response
        def api_response(data=None, status_code=200, success=True, message=None):
            payload = {}
            if success is not None:
                payload["success"] = success
            if message is not None:
                payload["message"] = message
            if data is not None:
                payload["data"] = data
            return _drf_response.Response(payload, status=status_code)

from apps.transactions.models import (
    Proposal, ProposalLine,
    Order, OrderLine,
    Invoice, InvoiceLine,
    Purchase, PurchaseLine,
    WorkOrder, WorkOrderLine,
    Requisition, RequisitionLine,
)
from apps.transactions.serializers.line_serializers import (
    ProposalSerializer, ProposalLineSerializer,
    OrderSerializer, OrderLineSerializer,
    InvoiceSerializer, InvoiceLineSerializer,
    PurchaseSerializer, PurchaseLineSerializer,
    WorkOrderSerializer, WorkOrderLineSerializer,
    RequisitionSerializer, RequisitionLineSerializer,
)
from apps.transactions.views.line_views import BasePermission, DefaultPagination
from apps.transactions.aggregation import compute_line_aggregate
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
from apps.core.constants.model_registry import get_model_meta, import_model


# Mapping helpers -----------------------------------------------------------
HEADER_MAP = {
    'proposal': (Proposal, ProposalSerializer, ProposalLine, ProposalLineSerializer),
    'order': (Order, OrderSerializer, OrderLine, OrderLineSerializer),
    'invoice': (Invoice, InvoiceSerializer, InvoiceLine, InvoiceLineSerializer),
    'purchase-order': (Purchase, PurchaseSerializer, PurchaseLine, PurchaseLineSerializer),
    'workorder': (WorkOrder, WorkOrderSerializer, WorkOrderLine, WorkOrderLineSerializer),
    'requisition': (Requisition, RequisitionSerializer, RequisitionLine, RequisitionLineSerializer),
}

# Replace hard-coded variant keys with canonical keys
MODEL_MAP = {
    # canonical keys only
    'requisition': (Requisition, RequisitionSerializer, RequisitionLine, RequisitionLineSerializer),
    # add other models here using canonical snake_case keys...
}


class _KindMixin:
    """Extracts kind from URL kwargs and exposes model + serializer accessors."""
    kind: Optional[str] = None

    def _resolve(self) -> Tuple[Type, Type, Type, Type]:
        kind = self.kind or ''
        mapping = HEADER_MAP.get(kind)
        if not mapping:
            raise ValueError(f"Unsupported transaction kind '{kind}'")
        return mapping  # header_model, header_serializer, line_model, line_serializer

    def get_header_model(self):
        return self._resolve()[0]

    def get_header_serializer(self):
        return self._resolve()[1]

    def get_line_model(self):
        return self._resolve()[2]

    def get_line_serializer(self):
        return self._resolve()[3]

    def initialize_kind(self, **kwargs):  # called from dispatch in subclasses
        k = kwargs.get('kind')
        if isinstance(k, str):
            self.kind = k


class TransactionHeaderListCreate(_KindMixin, generics.ListCreateAPIView):
    """Unified list/create endpoint for any transaction header kind.

    GET /api/tx/<kind>/  (paginated list)
    POST /api/tx/<kind>/ { ...fields... }
    """
    permission_classes = [BasePermission]
    pagination_class = DefaultPagination

    def dispatch(self, request, *args, **kwargs):
        self.initialize_kind(**kwargs)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        Model = self.get_header_model()
        return Model.objects.active().order_by('-id')

    def get_serializer_class(self):
        return self.get_header_serializer()


class TransactionHeaderDetail(_KindMixin, generics.RetrieveUpdateDestroyAPIView):
    """Retrieve/Update/Delete for a header kind."""
    permission_classes = [BasePermission]

    def dispatch(self, request, *args, **kwargs):
        self.initialize_kind(**kwargs)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return self.get_header_model().objects.active()

    def get_serializer_class(self):
        return self.get_header_serializer()


class TransactionLineListCreate(_KindMixin, generics.ListCreateAPIView):
    """List/Create lines nested under a header.

    GET /api/tx/<kind>/<id>/lines/
    POST /api/tx/<kind>/<id>/lines/ {...fields except parent...}
    """
    permission_classes = [BasePermission]
    pagination_class = DefaultPagination

    def dispatch(self, request, *args, **kwargs):
        self.initialize_kind(**kwargs)
        self.header_id = kwargs.get('pk')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        LineModel = self.get_line_model()
        return LineModel.objects.filter(parent_id=self.header_id).order_by('-id')

    def get_serializer_class(self):
        return self.get_line_serializer()

    def perform_create(self, serializer):
        HeaderModel = self.get_header_model()
        parent = get_object_or_404(HeaderModel, pk=self.header_id)
        serializer.save(parent=parent)


class TransactionLineDetail(_KindMixin, generics.RetrieveUpdateDestroyAPIView):
    """Retrieve/Update/Delete a specific line within a header.

    GET /api/tx/<kind>/<id>/lines/<line_pk>/
    """
    permission_classes = [BasePermission]
    lookup_url_kwarg = 'line_pk'

    def dispatch(self, request, *args, **kwargs):
        self.initialize_kind(**kwargs)
        self.header_id = kwargs.get('pk')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        LineModel = self.get_line_model()
        # Ensure line belongs to the header id context
        return LineModel.objects.filter(parent_id=self.header_id)

    def get_serializer_class(self):
        return self.get_line_serializer()

    def update(self, request, *args, **kwargs):  # ensure parent immutability via path
        # Strip parent if provided to prevent reassignment
        if isinstance(request.data, dict) and 'parent' in request.data:
            mutable_data = request.data.copy()
            mutable_data.pop('parent', None)
            request._full_data = mutable_data  # type: ignore
        return super().update(request, *args, **kwargs)


# Lightweight kind discovery endpoint (optional future): could list supported kinds.


@extend_schema(
    summary="Preview totals for a header",
    parameters=[OpenApiParameter(name='include_breakdown', required=False, type=bool, description='Include per-model breakdown (0/1)')],
    responses={200: OpenApiResponse(description='Aggregate totals payload in unified envelope')}
)
class TransactionTotalsPreview(_KindMixin, generics.GenericAPIView):
    """Read-only totals preview for a header using line aggregation.

    GET /api/tx/<kind>/<id>/preview-totals/?include_breakdown=1
    """
    permission_classes = [BasePermission]

    def dispatch(self, request, *args, **kwargs):
        self.initialize_kind(**kwargs)
        self.header_id = kwargs.get('pk')
        return super().dispatch(request, *args, **kwargs)

    # Provide queryset so ViewEditPermission can resolve model for permission rules
    def get_queryset(self):
        return self.get_header_model().objects.active()

    def get(self, request, *args, **kwargs):  # noqa: D401
        """Return aggregate totals for this header's lines.

        By default, scopes aggregation to this kind's line model (e.g., sales-order-line).
        Pass include_breakdown=1 to include per-model breakdown (useful if future variants
        also link to the same header id).
        """
        # Validate header id
        if self.header_id is None:
            return response.Response({'detail': 'Missing header id'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            header_id = int(self.header_id)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return response.Response({'detail': 'Invalid header id'}, status=status.HTTP_400_BAD_REQUEST)

        include_breakdown_param = request.query_params.get('include_breakdown')
        include_breakdown = include_breakdown_param in ('1', 'true', 'True', 'yes')
        kind = self.kind or ''
        model_key = f"{kind}-line" if kind else None
        try:
            data = compute_line_aggregate(header_id, model_key, include_breakdown=include_breakdown)
        except ValueError:
            return response.Response({'detail': 'Invalid kind'}, status=status.HTTP_400_BAD_REQUEST)
        return api_response(data=data)


def _resolve_models(token: str):
    """
    Accept any variant (TitleCase, kebab, underscore, plural), resolve to canonical key,
    and return model + serializer tuple from MODEL_MAP.
    """
    meta = get_model_meta(token)
    if not meta:
        raise Http404(f'Unknown model: {token}')
    key = meta.key  # canonical snake_case
    try:
        return MODEL_MAP[key]
    except KeyError:
        raise Http404(f'Unsupported model in this endpoint: {key}')


class LinkageCommentsView(generics.GenericAPIView):
    """
    GET /tx/linkages/<linkage_id>/comments/
    Returns: { data: { items: [ {source_model, source_id, text} ] } }
    """
    http_method_names = ["get", "options", "head"]

    def get(self, request, linkage_id: int, *args, **kwargs):
        try:
            lid = int(linkage_id)
        except Exception:
            return api_response(success=False, status_code=400, message="invalid_linkage_id")

        # Models to scan for linkage refs and comments
        model_names = [
            ("transactions", "ProposalLine"),
            ("transactions", "OrderLine"),
            ("transactions", "InvoiceLine"),
            ("transactions", "PurchaseLine"),
        ]
        items: List[Dict[str, Any]] = []

        for app_label, model_name in model_names:
            try:
                Model = apps.get_model(app_label, model_name)
            except Exception:
                continue
            # Only fetch relevant JSON fields if present
            fields = ["id"]
            for f in ("refs", "comments"):
                try:
                    Model._meta.get_field(f)  # type: ignore[attr-defined]
                    fields.append(f)
                except Exception:
                    pass

            qs = Model.objects.active()
            if len(fields) > 1:
                try:
                    qs = qs.only(*fields)
                except Exception:
                    pass

            for obj in qs:
                refs = getattr(obj, "refs", None) or {}
                try:
                    linkage_list = (refs.get("links") or {}).get("linkage") or []
                except Exception:
                    linkage_list = []
                has_linkage = False
                try:
                    has_linkage = lid in linkage_list
                except Exception:
                    # fallback if stored as strings
                    try:
                        has_linkage = str(lid) in [str(x) for x in linkage_list]
                    except Exception:
                        has_linkage = False
                if not has_linkage:
                    continue

                cm = getattr(obj, "comments", None) or {}
                # support both dict {'public': '...'} and plain string
                if isinstance(cm, dict):
                    comments_payload = cm
                else:
                    comments_payload = {"public": str(cm)} if cm else {}

                items.append({
                    "source_model": model_name,
                    "source_id": getattr(obj, "id", None),
                    "comments": comments_payload,
                })

        # Aggregate root comments (e.g., collect all public comments)
        comments_root: Dict[str, Any] = {"general": {}}
        public_comments = [
             it.get("comments", {}).get("public")
             for it in items
             if isinstance(it.get("comments"), dict) and it.get("comments", {}).get("public")
         ]
        # Always expose 'general.public' key for clients/tests
        comments_root["general"]["public"] = public_comments

        # Return raw payload; envelope middleware will set {"data": {...}}
        return response.Response({"items": items, "comments": comments_root}, status=status.HTTP_200_OK)


class WCAIPSaveView(views.APIView):
    """
    POST /tx/wcaip/save
    { "entity": "project", "data": { ...fields... } }
    """
    http_method_names = ["post", "options", "head"]

    def post(self, request, *args, **kwargs):
        body: Dict[str, Any] = request.data or {}
        entity = (body.get("entity") or "").strip().lower()
        data: Dict[str, Any] = body.get("data") or {}

        if entity == "project":
            Project = apps.get_model("transactions", "Project")
            allowed = ["situation", "objective", "priority", "status", "attention", "intent", "category", "contact_id"]
            create_kwargs = {k: data.get(k) for k in allowed if data.get(k) is not None}
            obj = Project.objects.create(**create_kwargs)
            return response.Response({"id": obj.pk}, status=status.HTTP_201_CREATED)

        return response.Response({"detail": "unsupported entity"}, status=status.HTTP_400_BAD_REQUEST)
