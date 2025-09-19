from __future__ import annotations

from typing import TYPE_CHECKING, Iterable, cast
from django.apps import apps as django_apps
from django.db import models
from django.db.models.query import QuerySet

from .base_transaction_model import TransactionBaseModel

class PurchaseOrder(TransactionBaseModel):
    class Meta:
        db_table = "purchase_orders"

    # Example method calling the totals service without import-time cycle
    def update_cost_totals(self, persist: bool = True) -> dict:
        from apps.transactions.services.po_totals import compute_purchase_order_cost_totals  # lazy import
        totals = compute_purchase_order_cost_totals(self)
        if persist:
            # ...persist totals on self as appropriate...
            self.save(update_fields=["dt_modified", "version"])
        return totals
    def open_lines(self) -> QuerySet["PurchaseOrderLine"]:
        POL = django_apps.get_model("transactions", "PurchaseOrderLine")
        qs = POL.objects.filter(parent=self, status__in=("open", "pending"))
        return cast(QuerySet["PurchaseOrderLine"], qs)
        return POL.objects.filter(parent=self, status__in=("open", "pending"))

if TYPE_CHECKING:  # pragma: no cover
    from .purchase_order_line import PurchaseOrderLine

__all__ = ["PurchaseOrder"]
