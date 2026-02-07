from __future__ import annotations

from django.db import models

from common.models import BaseModel


class InventoryMetricsSnapshot(BaseModel):
    @property
    def ida(self):
        return str(self.pk)

    @property
    def description(self):
        return f"Snapshot {self.dt_created}"

    """Periodic snapshot of summarized inventory metrics.

    Stores the JSON produced by summarize_inventory_metrics for time-series analysis.
    Keep lean; prune externally if growth becomes large.
    """

    metrics = models.JSONField()

    class Meta:
        indexes = [
            models.Index(fields=("id",), name="invmet_snapshot_id_idx"),
        ]
        ordering = ("-id",)

    def __str__(self):  # pragma: no cover
        return f"InventoryMetricsSnapshot#{self.pk} {self.dt_created}"

    # Standard manager (legacy suffix style support removed; use dt_created)
    objects = models.Manager()
