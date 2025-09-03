from __future__ import annotations

from django.db import models
from .item_base_model import ItemLinkedBase


class Service(ItemLinkedBase):
    """Extends an Item of kind=service with time / rate details."""

    rate_hourly = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True, help_text="Default billing rate")
    cost_hourly = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    process = models.JSONField(default=dict, blank=True, help_text="Process details or workflow steps for this service")
    travel = models.JSONField(default=dict, blank=True, help_text="Travel details or requirements for this service")
    timer = models.PositiveIntegerField(default=0, help_text="Timer duration in minutes")
    default_minutes = models.PositiveIntegerField(default=0)
    # .refs have related action

    class Meta:
        indexes = []  # inherited item index already present on base




# Take care of this in Actions
# CREATE TABLE IF NOT EXISTS "services" (
#     "action" VARCHAR(255),
#     "action_by" VARCHAR(255),
#     "attention" VARCHAR(255),
#     "attribute" VARCHAR(255),
#     "cause" VARCHAR(255),
#     "comment" TEXT,
#     "comment_public" TEXT,
#     "company" VARCHAR(255),
#     "cost_to_customer" INTEGER,
#     "cost_to_rep" INTEGER,
#     "cost_to_us" INTEGER,
#     "created_by" VARCHAR(255),
#     "description" VARCHAR(255),
#     "display" TEXT,
#     "duration_planned" INTEGER,
#     "expense_explain" TEXT,
#     "expenses" DOUBLE PRECISION,
#     "field_56" VARCHAR(255),
#     "is_tracked_sales" BOOLEAN DEFAULT FALSE,
#     "miles" INTEGER,
#     "price_service" DOUBLE PRECISION,
#     "price_travel" DOUBLE PRECISION,
#     "process" VARCHAR(255),
#     "publish" INTEGER,
#     "purpose" VARCHAR(255),
#     "references" JSONB,
#     "timer" INTEGER,
#     "travel_time" INTEGER
# );
