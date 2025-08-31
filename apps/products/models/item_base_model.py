from __future__ import annotations

from django.db import models
from common.models import BaseModel


class ItemLinkedBase(BaseModel):
		"""Abstract helper for models that attach additional domain-specific
		data to a catalog `Item` (e.g. service detail, regulatory profile, marketing
		content, extended specs). Provides a uniform FK + status flag so generic
		admin / API tooling can treat all extensions consistently.

		Rationale:
		- Avoid repeating the `item` FK + optional status pattern across many
			ancillary tables.
		- Inherit BaseModel for universal JSON envelopes (metadata, refs, etc.).
		- Keep lean: concrete subclasses add their own fields; this class should
			remain stable to minimize migration churn.

		Design note on identity:
		- We deliberately DO NOT duplicate `item.uuid` or `item.ida` here (or on any
			extension tables). The canonical identity facets live only on the primary
			`Item` row: `id` (PK, internal), `uuid` (stable cross‑database global id),
			and optional `ida` (human/source declared soft id). This keeps referential
			updates trivial (no fan‑out sync) and prevents divergence if an upstream
			source changes a soft identifier. Extensions should always resolve through
			`item_id` and, when needed externally, fetch the item's uuid/ida via join.
		"""

		item = models.ForeignKey('products.Item', on_delete=models.CASCADE, related_name="%(class)s_related")
		status = models.CharField(max_length=30, blank=True, db_index=True, help_text="Optional lifecycle / state label")

		class Meta:
				abstract = True
				indexes = [
						models.Index(fields=("item",), name="itemlinked_item_idx"),
				]

		def __str__(self):  # pragma: no cover - simple representation
				base = getattr(self, 'id', None)
				return f"{self.__class__.__name__}#{base or 'unsaved'} for Item {getattr(self, 'item_id', '?')}"

# NOTE:
# Existing concrete models (e.g. Service) can optionally inherit from this
# in the future; for initial scaffold we leave them independent to avoid
# introducing cross-migration ordering complexity. To adopt, change:
#   class Service(BaseModel): -> class Service(ItemLinkedBase):
# then remove its own status/item duplication if present.