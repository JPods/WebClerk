from __future__ import annotations

from django.db import models
from django.utils.text import slugify
from .item_base_model import ItemLinkedBase
from common.stats_mixin import StatsMixin


def default_profiles():
    return {}


def default_docs():
    return {}


def default_applies():
    return {}


class Specification(StatsMixin, ItemLinkedBase):
    """Specification or attribute for an item.

    Supports multiple value types (text / numeric / boolean / enum). Only one value_* field
    should be populated per record; value_type indicates which.
    """

    name = models.CharField(max_length=120, db_index=True)
    slug = models.SlugField(max_length=140, db_index=True, blank=True)
    description = models.CharField(max_length=255, blank=True)
    description_long = models.TextField(blank=True)
    value_text = models.CharField(max_length=255, blank=True)
    value_number = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
    value_bool = models.BooleanField(null=True, blank=True)
    value_type = models.CharField(max_length=20, blank=True, help_text="text|number|bool|enum")
    unit = models.CharField(max_length=30, blank=True)
    profiles = models.JSONField(default=default_profiles, blank=True)
    docs = models.JSONField(default=default_docs, blank=True)
    applies_to = models.JSONField(default=default_applies, blank=True)
    # volumen of sales, number of items, 
    # number of returns, margins, margin velocity
    # across all times using based on this specification

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["item", "name"], name="uniq_item_spec_name"),
            models.CheckConstraint(
                check=(
                    (models.Q(value_text__gt="") & models.Q(value_number__isnull=True) & models.Q(value_bool__isnull=True))
                    | (models.Q(value_text="") & models.Q(value_number__isnull=False) & models.Q(value_bool__isnull=True))
                    | (models.Q(value_text="") & models.Q(value_number__isnull=True) & models.Q(value_bool__isnull=False))
                    | (models.Q(value_text="") & models.Q(value_number__isnull=True) & models.Q(value_bool__isnull=True))  # allow empty pre-population
                ),
                name="spec_single_value_constraint",
            ),
        ]
        indexes = [
            models.Index(fields=("item", "slug"), name="spec_item_slug_idx"),
            models.Index(fields=("item", "name"), name="spec_item_name_idx"),
        ]

    def clean(self):  # pragma: no cover
        if not self.slug:
            self.slug = slugify(self.name)[:140]
        if self.value_type:
            vt = self.value_type
            # Basic coherence adjustments
            if vt == "text" and not self.value_text:
                self.value_type = ""
            if vt == "number" and self.value_number is None:
                self.value_type = ""
            if vt == "bool" and self.value_bool is None:
                self.value_type = ""

    def save(self, *args, **kwargs):  # pragma: no cover
        if not self.slug:
            self.slug = slugify(self.name)[:140]
        super().save(*args, **kwargs)