from __future__ import annotations

from django.db import models
from django.utils import timezone


class Variant(models.Model):
    """Concrete materialized variant row for performance and clarity.

    Links a child item to its parent item with a normalized canonical key and attrs.
    Use parent_item + canonical_key unique constraint to ensure one row per variant.
    """

    item = models.OneToOneField('products.Item', on_delete=models.CASCADE, related_name='variant_row')
    parent_item = models.ForeignKey('products.Item', on_delete=models.CASCADE, related_name='variant_children')
    canonical_key = models.CharField(max_length=255, db_index=True)
    attrs = models.JSONField(default=dict, blank=True)
    set_uuid = models.UUIDField(db_index=True)
    variant_uuid = models.UUIDField(db_index=True, unique=True)
    dt_created = models.BigIntegerField(default=0, db_index=True)
    dt_modified = models.BigIntegerField(default=0, db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['parent_item', 'canonical_key'], name='uniq_parent_key'),
        ]
        indexes = [
            models.Index(fields=['parent_item'], name='variant_parent_idx'),
        ]

    def save(self, *args, **kwargs):  # pragma: no cover simple
        now_ms = int(timezone.now().timestamp() * 1000)
        if not self.pk and not self.dt_created:
            self.dt_created = now_ms
        self.dt_modified = now_ms
        return super().save(*args, **kwargs)

    def __str__(self):  # pragma: no cover
        iid = getattr(self, 'item_id', None)
        pid = getattr(self, 'parent_item_id', None)
        return f"Variant(item={iid}, parent={pid}, key={self.canonical_key})"
