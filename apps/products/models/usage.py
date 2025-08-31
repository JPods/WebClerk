from __future__ import annotations

from decimal import Decimal
from django.db import models
from .item_base_model import ItemLinkedBase


class ItemUsage(ItemLinkedBase):
    """Monthly usage summary for an item."""

    year = models.PositiveSmallIntegerField()
    month = models.PositiveSmallIntegerField()
    qty_sold = models.DecimalField(max_digits=14, decimal_places=4, default=Decimal("0"))
    qty_purchased = models.DecimalField(max_digits=14, decimal_places=4, default=Decimal("0"))
    qty_returned = models.DecimalField(max_digits=14, decimal_places=4, default=Decimal("0"))

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["item", "year", "month"], name="uniq_item_year_month"),
        ]
        indexes = [
            models.Index(fields=("year", "month"), name="usage_year_month_idx"),
        ]

# CREATE TABLE IF NOT EXISTS "usages" (
#     "item_id" BIGSERIAL,
#     "actual_turns" DOUBLE PRECISION,
#     "adjustment_quantity" DOUBLE PRECISION,
#     "adjustment_value" DOUBLE PRECISION,
#     "average_turn" DOUBLE PRECISION,
#     "bom_quantity_actual" DOUBLE PRECISION,
#     "capacity" DOUBLE PRECISION,
#     "cost_actual" DOUBLE PRECISION,
#     "cost_plan" DOUBLE PRECISION,
#     "count_invoices" INTEGER,
#     "count_sos" INTEGER,
#     "description" VARCHAR(255),
#     "inventory_actual" DOUBLE PRECISION,
#     "inventory_eom_count" DOUBLE PRECISION,
#     "inventory_plan" DOUBLE PRECISION,
#     "lead_time" DOUBLE PRECISION,
#     "margin_factor" DOUBLE PRECISION,
#     "order_quantity_actual" DOUBLE PRECISION,
#     "order_quantity_plan" DOUBLE PRECISION,
#     "order_value_actual" DOUBLE PRECISION,
#     "order_value_plan" DOUBLE PRECISION,
#     "purchase_quantity" DOUBLE PRECISION,
#     "purchase_value" DOUBLE PRECISION,
#     "purpose" VARCHAR(255),
#     "sales_actual" DOUBLE PRECISION,
#     "sales_plan" DOUBLE PRECISION,
#     "sales_quantity_actual" DOUBLE PRECISION,
#     "sales_quantity_plan" DOUBLE PRECISION,
#     "scrap_actual" DOUBLE PRECISION,
#     "scrap_plan" DOUBLE PRECISION,
#     "target_turns" DOUBLE PRECISION,
#     "type" VARCHAR(255)