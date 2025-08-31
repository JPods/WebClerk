from __future__ import annotations

from django.db import models
from .item_base_model import ItemLinkedBase


class ItemCarried(ItemLinkedBase):
    """Association indicating an organization (typically customer) carries an item.

    Notes:
      - Uses ItemLinkedBase.item FK; we add explicit org FK here.
      - table_name removed; org_type is available via org.org_type.
      - description is optional free-form context (planogram, notes).
    """

    org = models.ForeignKey('orgs.OrgBase', on_delete=models.CASCADE, related_name="items_carried")
    description = models.CharField(max_length=255, blank=True)
    security_level = models.IntegerField(default=0, db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["item", "org"], name="uniq_item_org_carried"),
        ]
        indexes = [
            models.Index(fields=("org", "item"), name="carried_org_item_idx"),
        ]
