from __future__ import annotations

from django.db import models


class InventoryMetricsSnapshot(models.Model):
    """Periodic snapshot of summarized inventory metrics.

    Stores the JSON produced by summarize_inventory_metrics for time-series analysis.
    Keep lean; prune externally if growth becomes large.
    """

    dt_created = models.DateTimeField(auto_now_add=True, db_index=True)
    metrics = models.JSONField()

    class Meta:
        indexes = [
            models.Index(fields=("dt_created",), name="invmet_snapshot_created_idx"),
        ]
        ordering = ("-dt_created",)

    def __str__(self):  # pragma: no cover
        return f"InventoryMetricsSnapshot#{self.pk} {self.dt_created}"

    # Standard manager (legacy suffix style support removed; use dt_created)
    objects = models.Manager()
