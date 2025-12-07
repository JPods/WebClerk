from typing import Dict
from django.db import models
from .base_transaction_model import TransactionBaseModel
from apps.transactions.services.sales_order_totals import compute_sales_order_sell_cost_totals

class SalesOrder(TransactionBaseModel):
    class Meta:
        db_table = "sales_orders"

    # Allow SalesOrder.objects.create(order_no="...") without a DB column
    @property
    def order_no(self) -> str:
        return getattr(self, "_transient_order_no", "")

    @order_no.setter
    def order_no(self, value: str) -> None:
        self._transient_order_no = value

    # Optional alias: name proxies to order_no
    @property
    def name(self) -> str:
        return getattr(self, "_transient_order_no", "") or getattr(self, "_transient_name", "")

    @name.setter
    def name(self, value: str) -> None:
        self._transient_order_no = value
        self._transient_name = value

    def update_sell_cost_totals(self, persist: bool = False) -> Dict[str, Dict[str, float]]:
        """Compute sell/cost/totals from lines. If persist=True and fields exist, save them."""
        computed = compute_sales_order_sell_cost_totals(self)

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
        return self.order_no or str(getattr(self, "ida", "")) or f"SalesOrder({self.pk})"


__all__ = ["SalesOrder"]