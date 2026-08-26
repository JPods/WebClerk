from __future__ import annotations

from django.db import models
from common.models import BaseModel


class ItemLinkedBase(BaseModel):
	"""Abstract base for models that link to a catalog Item.

	Provides:
	- item FK (the machine — all joins and DB operations use item_id)
	- item_ida CharField (the human — denormalized display identifier)
	- description CharField (the human — what this record is about)
	- status CharField (lifecycle label)

	item_ida and description are display fields for humans looking at records.
	They are populated from the parent Item on save if not already set.
	All DB operations (joins, filters, FKs) use item_id, never item_ida.
	"""

	item = models.ForeignKey(
		'products.Item', on_delete=models.CASCADE,
		related_name="%(class)s_related", db_column='item_id',
	)
	item_ida = models.CharField(
		max_length=120, blank=True, db_index=True,
		help_text="Item identifier — denormalized from Item.ida for display",
	)
	description = models.CharField(
		max_length=255, blank=True,
		help_text="Human-readable description",
	)
	# status inherited from BaseModel → LifecycleMixin

	class Meta:
		abstract = True

	def save(self, *args, **kwargs):
		# Populate display fields from parent Item if not set
		if self.item_id and not self.item_ida:
			try:
				self.item_ida = self.item.ida or ''
			except Exception:
				pass
		if self.item_id and not self.description:
			try:
				self.description = self.item.name or self.item.ida or ''
			except Exception:
				pass
		super().save(*args, **kwargs)

	@property
	def item_ida_value(self):
		return self.item_ida or str(self.pk)

	def __str__(self):
		base = getattr(self, 'id', None)
		label = self.item_ida or (f'Item {self.item_id}' if self.item_id else '?')
		return f"{self.__class__.__name__}#{base or 'unsaved'} ({label})"
