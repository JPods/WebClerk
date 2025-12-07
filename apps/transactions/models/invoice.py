from typing import Dict
from django.db import models
from .base_transaction_model import TransactionBaseModel
from apps.transactions.services.invoice_totals import compute_invoice_sell_cost_totals


class Invoice(TransactionBaseModel):
    class Meta:
        db_table = "invoices"

    # JSONB fields for references and metadata
    refs = models.JSONField(default=dict, blank=True, null=True, help_text="References like order_id")
    metadata = models.JSONField(default=dict, blank=True, null=True, help_text="Payment history and balances")

    def update_sell_cost_totals(self, persist: bool = False) -> Dict[str, Dict[str, float]]:
        computed = compute_invoice_sell_cost_totals(self)
        if persist:
            update_fields: list[str] = []
            if hasattr(self, "sell"):
                self.sell = computed["sell"]; update_fields.append("sell")
            if hasattr(self, "cost"):
                self.cost = computed["cost"]; update_fields.append("cost")
            if hasattr(self, "totals"):
                self.totals = computed["totals"]; update_fields.append("totals")
            if update_fields:
                update_fields += ["dt_modified", "version"]
                self.save(update_fields=update_fields)
        return computed

    def __str__(self) -> str:
        return f"Invoice #{self.id} ({self.ida or ''})"


__all__ = ["Invoice"]