from django.db import models
from common.models import BaseModel
from django.core.exceptions import ValidationError
from apps.core.choices import SETTING_PURPOSE_CHOICES
from apps.core.constants.model_registry import VALID_MODEL_NAMES, get_model_meta, get_model_meta_by_endpoint
# company, defaults, view_edit, user-levels,
# poppups, question, constants, integrations, notifications,
# 
class Setting(BaseModel):
    name = models.CharField(max_length=255, blank=True, null=True)
    purpose = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        choices=SETTING_PURPOSE_CHOICES,
    )
    role = models.CharField(max_length=255, blank=True, null=True)
    # Canonical model identifier (parent_model-only)
    parent_model = models.CharField(max_length=255, blank=True, null=True)
    data = models.JSONField(blank=True, null=True)
    

    class Meta:
        db_table = 'settings'

    def __str__(self):
        return f"{self.name or 'Setting'} ({self.id})"

    def clean(self):  # enforce canonical names when provided
        super().clean()
        # Validate parent_model if provided; accept canonical key, endpoint slug, or simple singular/plural variants.
        target = (self.parent_model or '').strip().lower() if self.parent_model else None
        if not target:
            return
        meta = get_model_meta(target) or get_model_meta_by_endpoint(target)
        if not meta:
            raise ValidationError({'parent_model': f"Invalid parent_model '{target}'. Must be one of: {', '.join(VALID_MODEL_NAMES)}"})
        # Store canonical singular key
        self.parent_model = meta.key
    
    def save(self, *args, **kwargs):
        """Ensure parent_model is normalized/validated even when created directly.

        Django doesn't call clean() automatically on save. We enforce it here so
        records created via ORM (bypassing serializers) still store canonical parent_model.
        """
        # Use full_clean to include clean() and field validation; ignore unique checks at DB level.
        try:
            self.full_clean()
        except ValidationError:
            # Re-raise to surface up to callers (API should translate to 400)
            raise
        return super().save(*args, **kwargs)
    
    # Treat "comment" as a virtual field backed by data["comment"]
    @property
    def comment(self) -> str:
        d = getattr(self, "data", {}) or {}
        return str(d.get("comment") or "")

    @comment.setter
    def comment(self, value: str) -> None:
        d = dict(getattr(self, "data", {}) or {})
        d["comment"] = "" if value is None else str(value)
        self.data = d

#QQQ look at documents as a model
# we have settings record for each table that
# lists the fields that are denormalized into .refs.keywords.
# settings.parent_model = canonical model name and settings.purpose = keywords
# settings.data contains an object listing fields 
# for the values to be denormalized into keywords.

# Purposes registry (see readmes/settings.md for shapes):
# - view_edit: per-table field visibility/edit matrix by role
# - constants: global user-defined constants map
# - db_defaults: global database/platform defaults
# - sales_defaults: sales module defaults (global or per table)
# - purchase_defaults: purchasing module defaults (global or per table)
# - accounting_defaults: accounting/GL/tax defaults

#Logic now:
# Reads active Setting with purpose='keywords' for the documents table.
# Accepts data.fields (list/tuple) or comma string (data.field_list fallback).
# On create: always enqueue (unless duplicate unprocessed Pending exists).
# On update: only enqueue if any tracked keyword field actually changed.
# Debounce: skips creating a new Pending if an unprocessed one already exists for the same table/record.
# Fallback: if no tracked fields configured but table in get_keyword_requirements(), only enqueue on create.
# Includes tracked_fields list in Pending.data for transparency.
# Guarded against errors; won’t break saves.

