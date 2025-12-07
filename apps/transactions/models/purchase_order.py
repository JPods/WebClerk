from __future__ import annotations

from typing import Dict, TYPE_CHECKING
from django.db import models

from .base_transaction_model import TransactionBaseModel
from apps.transactions.services.purchase_order_totals import compute_purchase_order_sell_cost_totals

class PurchaseOrder(TransactionBaseModel):
    class Meta:
        db_table = "purchase_orders"

    # Allow PurchaseOrder.objects.create(po_no="...") without a DB column
    @property
    def po_no(self) -> str:
        return getattr(self, "_transient_po_no", "")

    @po_no.setter
    def po_no(self, value: str) -> None:
        self._transient_po_no = value

    # Optional alias: name proxies to po_no
    @property
    def name(self) -> str:
        return getattr(self, "_transient_po_no", "") or getattr(self, "_transient_name", "")

    @name.setter
    def name(self, value: str) -> None:
        self._transient_po_no = value
        self._transient_name = value

    def update_sell_cost_totals(self, persist: bool = False) -> Dict[str, Dict[str, float]]:
        """Compute sell/cost/totals from lines. For PO, sell is empty, cost is aggregated."""
        computed = compute_purchase_order_sell_cost_totals(self)

        if persist:
            update_fields: list[str] = []
            if hasattr(self, "sell"):
                self.sell = computed["sell"]  # type: ignore[assignment]
                update_fields.append("sell")
            if hasattr(self, "cost"):
                self.cost = computed["cost"]  # type: ignore[assignment]
                update_fields.append("cost")
            if hasattr(self, "totals"):
                self.totals = computed["totals"]  # type: ignore[assignment]
                update_fields.append("totals")
            if update_fields:
                update_fields += ["dt_modified", "version"]
                self.save(update_fields=update_fields)

        return computed

    def __str__(self) -> str:
        return f"PurchaseOrder #{self.id} ({self.po_no or ''})"

if TYPE_CHECKING:  # pragma: no cover
    from .purchase_order_line import PurchaseOrderLine

__all__ = ["PurchaseOrder"]
