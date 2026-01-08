from __future__ import annotations

from django.db import models

from apps.products.choices import PROCESSOR_RUN_TYPE_CHOICES


class InventoryAdjustmentProcessorRun(models.Model):
    """Audit log of each pending adjustment processor invocation."""

    RUN_GLOBAL = 'global'
    RUN_STACK = 'stack'
    RUN_TYPES = PROCESSOR_RUN_TYPE_CHOICES

    run_type = models.CharField(max_length=12, choices=RUN_TYPES, db_index=True)
    stack_id = models.IntegerField(null=True, blank=True, db_index=True)
    dt_started = models.DateTimeField()
    dt_finished = models.DateTimeField()
    duration_s = models.DecimalField(max_digits=10, decimal_places=3)
    attempted = models.IntegerField(default=0)
    applied = models.IntegerField(default=0)
    skipped_locked = models.IntegerField(default=0)
    still_locked = models.IntegerField(default=0)
    insufficient = models.IntegerField(default=0)
    canceled = models.IntegerField(default=0)
    reserved_conflict_skipped = models.IntegerField(default=0)
    dry_run = models.BooleanField(default=False)
    summary = models.JSONField(default=dict, blank=True)

    dt_created = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=("run_type", "dt_created"), name="invproc_run_type_created_idx"),
        ]
        ordering = ("-dt_created",)

    def __str__(self):  # pragma: no cover
        return f"ProcRun#{self.pk}:{self.run_type}:{self.attempted}/{self.applied}"
