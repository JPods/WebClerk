import uuid
from django.db import models
from common.models import BaseModel
from django.core.exceptions import ValidationError
from apps.core.constants.table_registry import VALID_MODEL_KEYS, TABLE_REGISTRY_BY_ENDPOINT
# company, defaults, view_edit, user-levels,
# poppups, question, constants, integrations, notifications,
# 
class Setting(BaseModel):
    name = models.CharField(max_length=255, blank=True, null=True)
    purpose = models.CharField(max_length=255, blank=True, null=True)
    role = models.CharField(max_length=255, blank=True, null=True)
    # Canonical model identifier (model_name-only)
    model_name = models.CharField(max_length=255, blank=True, null=True)
    data = models.JSONField(blank=True, null=True)
    

    class Meta:
        db_table = 'settings'

    def __str__(self):
        return f"{self.name or 'Setting'} ({self.id})"

    def clean(self):  # enforce canonical names when provided
        super().clean()
        # Validate model_name if provided; accept canonical key, endpoint slug, or simple singular/plural variants.
        target = (self.model_name or '').strip().lower() if self.model_name else None
        if not target:
            return
        key = None
        # 1) Exact registry key
        if target in VALID_MODEL_KEYS:
            key = target
        # 2) Endpoint slug
        elif target in TABLE_REGISTRY_BY_ENDPOINT:
            key = TABLE_REGISTRY_BY_ENDPOINT[target].key
        # 3) Singular provided (e.g., 'sales_order_line'): try plural + 's'
        elif target + 's' in VALID_MODEL_KEYS:
            key = target + 's'
        if not key:
            raise ValidationError({'model_name': f"Invalid model_name '{target}'. Must be one of: {', '.join(VALID_MODEL_KEYS)}"})
        # Store singular form consistently (drop a single trailing 's' when present)
        self.model_name = key[:-1] if key.endswith('s') else key
    
    def save(self, *args, **kwargs):
        """Ensure model_name is normalized/validated even when created directly.

        Django doesn't call clean() automatically on save. We enforce it here so
        records created via ORM (bypassing serializers) still store canonical model_name.
        """
        # Use full_clean to include clean() and field validation; ignore unique checks at DB level.
        try:
            self.full_clean()
        except ValidationError:
            # Re-raise to surface up to callers (API should translate to 400)
            raise
        return super().save(*args, **kwargs)
    

#QQQ look at documents as a model
# we have settings record for each table that
# lists the fields that are denormalized into .refs.keywords.
# settings.model_name = canonical model name and settings.purpose = keywords
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

