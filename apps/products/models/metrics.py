from __future__ import annotations

from django.db import models


class InventoryMetricsSnapshot(models.Model):
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

    # dt_created is inherited from BaseModel/CoreModel
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
