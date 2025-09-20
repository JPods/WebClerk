from __future__ import annotations

from typing import TYPE_CHECKING, cast
from django.apps import apps as django_apps
from django.db import models
from django.db.models.query import QuerySet

from .base_transaction_model import TransactionBaseModel

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

if TYPE_CHECKING:  # pragma: no cover
    from .purchase_order_line import PurchaseOrderLine

__all__ = ["PurchaseOrder"]
