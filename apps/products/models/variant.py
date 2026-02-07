from __future__ import annotations

from django.db import models

from common.models import BaseModel


class Variant(BaseModel):

    """Concrete materialized variant row for performance and clarity.

    Links a child item to its parent item with a normalized canonical key and attrs.
    Use item_id + canonical_key unique constraint to ensure one row per variant.
    """

    item_ida = models.CharField(max_length=120, blank=True, db_index=True, help_text="String identifier for this variant")
    description = models.CharField(max_length=255, blank=True, help_text="Description for this variant")

    item = models.OneToOneField('products.Item', on_delete=models.CASCADE, related_name='variant_row')
    parent_item = models.ForeignKey('products.Item', on_delete=models.CASCADE, related_name='variant_children')
    canonical_key = models.CharField(max_length=255, db_index=True)
    attrs = models.JSONField(default=dict, blank=True)
    set_uuid = models.UUIDField(db_index=True)
    variant_uuid = models.UUIDField(db_index=True, unique=True)

    @property
    def ida(self):
        return str(self.pk)

    @property
    def item_ida_value(self):
        return self.item_ida or str(self.pk)

    @property
    def description_value(self):
        return self.description or self.canonical_key

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['parent_item', 'canonical_key'], name='uniq_parent_key'),
        ]
        indexes = [
            models.Index(fields=['parent_item'], name='variant_parent_idx'),
        ]

    def __str__(self):  # pragma: no cover
        iid = getattr(self, 'item_id', None)
        pid = getattr(self, 'parent_item_id', None)
        return f"Variant(item={iid}, parent={pid}, key={self.canonical_key})"
