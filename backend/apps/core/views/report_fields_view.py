"""
Report field registry — returns available fields for a model, grouped by source.

Used by the Report Designer to populate the field picker.

qqqReview by 2026-09-10: access is restricted to admin only via
REPORT_FIELD_REGISTRY_RESTRICTED. Set to False during development.
Once the designer is stable, set True and enforce is_superuser.

GET /wcapi/report-fields/?model=order
  → { direct: [...], related: {...}, json_paths: [...], lines: [...] }
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from django.db import models
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.services.wcapi_registry import get_model

logger = logging.getLogger(__name__)

# qqqReview by 2026-09-10: set True when report designer access control is finalized
REPORT_FIELD_REGISTRY_RESTRICTED = False


# ── Field type mapping ──────────────────────────────────────────────

_DJANGO_TO_FIELD_TYPE = {
    models.CharField: "text",
    models.TextField: "text",
    models.IntegerField: "number",
    models.BigIntegerField: "number",
    models.SmallIntegerField: "number",
    models.PositiveIntegerField: "number",
    models.FloatField: "number",
    models.DecimalField: "money",
    models.BooleanField: "checkbox",
    models.DateField: "date",
    models.DateTimeField: "date",
    models.EmailField: "text",
    models.URLField: "text",
    models.UUIDField: "text",
    models.JSONField: "json",
}

# Known JSON field paths per model — these are the common nested keys
# inside BaseModel's metadata, refs, config, totals, etc.
_JSON_PATHS = {
    "_base": {
        "metadata": [
            "metadata.flow",
            "metadata.health.rating",
            "metadata.priority",
            "metadata.source",
        ],
        "refs": [
            "refs.tags",
            "refs.keywords",
        ],
    },
    "order": {
        "totals": [
            "totals.subtotal", "totals.tax", "totals.shipping",
            "totals.total", "totals.balance",
        ],
        "config": [
            "config.po_num", "config.ship_via", "config.fob",
        ],
    },
    "invoice": {
        "totals": [
            "totals.subtotal", "totals.tax", "totals.shipping",
            "totals.total", "totals.balance",
        ],
        "finance": [
            "finance.commission", "finance.discount_pct",
        ],
    },
    "purchase": {
        "totals": [
            "totals.subtotal", "totals.total",
        ],
    },
    "proposal": {
        "totals": [
            "totals.subtotal", "totals.tax", "totals.total",
        ],
    },
    "customer": {
        "aging": [
            "aging.balance_due", "aging.current",
            "aging.past_1_30", "aging.past_31_60", "aging.past_61",
        ],
    },
    "payment": {
        "totals": [
            "totals.total",
        ],
    },
    "workorder": {
        "totals": [
            "totals.materials", "totals.labor", "totals.total",
        ],
    },
}

# Related model fields accessible via refs.links or FK
_RELATED_FIELDS = {
    "order": {
        "customer": ["company", "attention", "address_full", "phone", "email", "ida"],
        "rep": ["name", "ida"],
    },
    "invoice": {
        "customer": ["company", "attention", "address_full", "phone", "email", "ida"],
        "rep": ["name", "ida"],
    },
    "purchase": {
        "vendor": ["company", "attention", "address_full", "phone", "email", "ida"],
    },
    "proposal": {
        "customer": ["company", "attention", "address_full", "phone", "email", "ida"],
    },
    "workorder": {
        "customer": ["company", "attention", "address_full", "phone", "email", "ida"],
    },
    "payment": {
        "customer": ["company", "attention", "address_full", "phone", "email", "ida"],
    },
    "customer": {
        "rep": ["name", "ida"],
    },
}

# Line model fields — what's available when using a table/panel
_LINE_FIELDS = {
    "order_line": [
        {"field": "item.ida", "label": "Item #", "type": "text"},
        {"field": "item.name", "label": "Item Name", "type": "text"},
        {"field": "item.description", "label": "Description", "type": "text"},
        {"field": "quantity.staged", "label": "Qty Ordered", "type": "qty"},
        {"field": "quantity.active", "label": "Qty Shipped", "type": "qty"},
        {"field": "price.unit", "label": "Unit Price", "type": "money"},
        {"field": "price.extended", "label": "Extended", "type": "money"},
        {"field": "price.discount_amount", "label": "Discount", "type": "money"},
        {"field": "cost.unit", "label": "Unit Cost", "type": "money"},
        {"field": "cost.extended", "label": "Extended Cost", "type": "money"},
        {"field": "tax.amount", "label": "Tax", "type": "money"},
        {"field": "commission.rate", "label": "Comm Rate", "type": "number"},
        {"field": "commission.amount", "label": "Comm Amt", "type": "money"},
        {"field": "physical.weight", "label": "Weight", "type": "number"},
        {"field": "item.bin", "label": "Bin Location", "type": "text"},
    ],
    "invoice_line": [
        {"field": "item.ida", "label": "Item #", "type": "text"},
        {"field": "item.name", "label": "Item Name", "type": "text"},
        {"field": "item.description", "label": "Description", "type": "text"},
        {"field": "quantity.staged", "label": "Qty Ordered", "type": "qty"},
        {"field": "quantity.active", "label": "Qty Shipped", "type": "qty"},
        {"field": "price.unit", "label": "Unit Price", "type": "money"},
        {"field": "price.extended", "label": "Extended", "type": "money"},
        {"field": "cost.unit", "label": "Unit Cost", "type": "money"},
        {"field": "cost.extended", "label": "Extended Cost", "type": "money"},
        {"field": "tax.amount", "label": "Tax", "type": "money"},
        {"field": "physical.weight", "label": "Weight", "type": "number"},
        {"field": "physical.country_of_origin", "label": "Origin", "type": "text"},
        {"field": "physical.hs_code", "label": "HS Code", "type": "text"},
    ],
    "purchase_line": [
        {"field": "item.ida", "label": "Item #", "type": "text"},
        {"field": "item.name", "label": "Item Name", "type": "text"},
        {"field": "item.description", "label": "Description", "type": "text"},
        {"field": "quantity.staged", "label": "Qty Ordered", "type": "qty"},
        {"field": "quantity.active", "label": "Qty Received", "type": "qty"},
        {"field": "cost.unit", "label": "Unit Cost", "type": "money"},
        {"field": "cost.extended", "label": "Extended", "type": "money"},
    ],
    "proposal_line": [
        {"field": "item.ida", "label": "Item #", "type": "text"},
        {"field": "item.name", "label": "Item Name", "type": "text"},
        {"field": "item.description", "label": "Description", "type": "text"},
        {"field": "quantity.staged", "label": "Qty", "type": "qty"},
        {"field": "price.unit", "label": "Unit Price", "type": "money"},
        {"field": "price.extended", "label": "Extended", "type": "money"},
    ],
}

# Map parent model to its line model
_MODEL_TO_LINE = {
    "order": "order_line",
    "invoice": "invoice_line",
    "purchase": "purchase_line",
    "proposal": "proposal_line",
}


# ── Introspect Django model fields ──────────────────────────────────

def _get_direct_fields(model_cls) -> List[Dict[str, Any]]:
    """Return direct (non-relation) fields from a Django model."""
    fields = []
    skip = {"id", "password", "last_login"}
    for f in model_cls._meta.get_fields():
        if f.name in skip:
            continue
        if isinstance(f, (models.ManyToManyField, models.ManyToManyRel,
                          models.ManyToOneRel, models.ForeignKey)):
            continue
        field_type = "text"
        for django_cls, ft in _DJANGO_TO_FIELD_TYPE.items():
            if isinstance(f, django_cls):
                field_type = ft
                break
        label = f.name.replace("_", " ").title()
        fields.append({
            "field": f.name,
            "label": label,
            "type": field_type,
            "source": "direct",
        })
    return sorted(fields, key=lambda x: x["field"])


# ── View ────────────────────────────────────────────────────────────

class ReportFieldsView(APIView):
    """
    GET /wcapi/report-fields/?model=order

    Returns available fields for the report designer, grouped by source.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # qqqReview by 2026-09-10: enforce admin restriction
        if REPORT_FIELD_REGISTRY_RESTRICTED:
            if not (request.user.is_superuser or request.user.is_staff):
                return Response(
                    {"error": "Report field registry requires admin access"},
                    status=403,
                )

        model_name = request.query_params.get("model", "").strip().lower()
        if not model_name:
            return Response(
                {"error": "model parameter required (e.g. ?model=order)"},
                status=400,
            )

        model_cls = get_model(model_name)
        if not model_cls:
            return Response(
                {"error": f"Unknown model: {model_name}"},
                status=404,
            )

        # 1. Direct fields from the model
        direct = _get_direct_fields(model_cls)

        # 2. Related model fields (via refs.links or FK)
        related = {}
        rel_defs = _RELATED_FIELDS.get(model_name, {})
        for rel_name, rel_fields in rel_defs.items():
            related[rel_name] = [
                {
                    "field": f"{rel_name}.{f}",
                    "label": f"{rel_name.title()} {f.replace('_', ' ').title()}",
                    "type": "text",
                    "source": "related",
                }
                for f in rel_fields
            ]

        # 3. JSON paths (totals, config, metadata, etc.)
        json_paths = []
        # Base paths available on all BaseModel descendants
        for group, paths in _JSON_PATHS.get("_base", {}).items():
            for p in paths:
                json_paths.append({
                    "field": p,
                    "label": p.replace(".", " ").replace("_", " ").title(),
                    "type": "text",
                    "source": "json",
                    "group": group,
                })
        # Model-specific paths
        for group, paths in _JSON_PATHS.get(model_name, {}).items():
            for p in paths:
                json_paths.append({
                    "field": p,
                    "label": p.split(".")[-1].replace("_", " ").title(),
                    "type": "money" if "total" in p or "tax" in p or "shipping" in p
                           or "balance" in p or "commission" in p or "discount" in p
                           else "text",
                    "source": "json",
                    "group": group,
                })

        # 4. Line fields (for table/panel insertion)
        line_model_key = _MODEL_TO_LINE.get(model_name)
        lines = _LINE_FIELDS.get(line_model_key, []) if line_model_key else []

        return Response({
            "model": model_name,
            "direct": direct,
            "related": related,
            "json_paths": json_paths,
            "lines": lines,
            "line_model": line_model_key,
        })
