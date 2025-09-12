from __future__ import annotations

from django.db import models


class LinkageIndex(models.Model):
    """Materialized index enforcing uniqueness of a record->linkage mapping.

    Each row represents that a specific table row (table_name, record_id)
    belongs to exactly one Linkage hub. This enables a simple DB-level
    uniqueness guarantee without refactoring existing JSON refs storage.
    """

    linkage = models.ForeignKey(
        'docs.Linkage', on_delete=models.CASCADE, related_name='index_entries'
    )
    table_name = models.CharField(max_length=255, db_index=True)
    record_id = models.IntegerField(db_index=True)

    class Meta:
        db_table = 'linkage_index'
        constraints = [
            models.UniqueConstraint(
                fields=['table_name', 'record_id'], name='uniq_linkage_index_pair'
            )
        ]
        indexes = [
            models.Index(fields=['linkage'], name='linx_lkg_idx'),
            models.Index(fields=['table_name', 'linkage'], name='linx_tbl_lkg_idx'),
        ]

    def __str__(self) -> str:  # pragma: no cover
        # Use getattr to avoid static analysis complaints about linkage_id
        return f"{self.table_name}:{self.record_id} -> {getattr(self, 'linkage_id', None)}"
