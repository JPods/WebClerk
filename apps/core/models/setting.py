import uuid
from django.db import models
from common.models import BaseModel
from django.core.exceptions import ValidationError
from apps.core.constants.table_registry import VALID_TABLE_NAMES, is_valid_table_name
# company, defaults, view_edit, user-levels,
# poppups, question, constants, integrations, notifications,
# 
class Setting(BaseModel):
    name = models.CharField(max_length=255, blank=True, null=True)
    purpose = models.CharField(max_length=255, blank=True, null=True)
    role = models.CharField(max_length=255, blank=True, null=True)
    table_name = models.CharField(max_length=255, blank=True, null=True)
    data = models.JSONField(blank=True, null=True)
    

    class Meta:
        db_table = 'settings'

    def __str__(self):
        return f"{self.name or 'Setting'} ({self.id})"

    def clean(self):  # enforce canonical table names when provided
        super().clean()
        if self.table_name:
            if self.table_name not in VALID_TABLE_NAMES:
                raise ValidationError({'table_name': f"Invalid table_name '{self.table_name}'. Must be one of: {', '.join(VALID_TABLE_NAMES)}"})
    

#QQQ look at documents as a model
# we have settings record for each table that
# lists the fields that are denormalized into .refs.keywords.
# settings.table_name = table_name and settings.purpose = keywords
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

