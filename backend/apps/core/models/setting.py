from django.db import models
from django.db.models import Q
from common.models import BaseModel
from django.core.exceptions import ValidationError
from apps.core.choices import SETTING_SCOPE_CHOICES
from apps.core.constants.model_registry import VALID_MODEL_NAMES, get_model_meta, get_model_meta_by_endpoint


class Setting(BaseModel):
    """Configuration record — stores layouts, defaults, field access, and behavior rules.

    Hierarchy (most specific wins):
      user (contact_id) → role → org (org_id) → system (scope='system')

    Use resolve_setting() to walk the chain and get the effective value.
    """
    name = models.CharField(max_length=255, blank=True, null=True)
    # Scope: who does this setting apply to?
    scope = models.CharField(
        max_length=20,
        choices=SETTING_SCOPE_CHOICES,
        default="system",
        db_index=True,
        help_text="system=everyone, org=one business, role=one role, user=one person",
    )
    role = models.CharField(max_length=255, blank=True, null=True)
    org_id = models.BigIntegerField(default=0, db_index=True, help_text="Organization ID — 0 = all orgs")
    contact_id = models.BigIntegerField(default=0, db_index=True, help_text="User contact ID — 0 = all users")
    # Canonical model identifier
    parent_model = models.CharField(max_length=255, blank=True, null=True)
    explanation = models.TextField(
        blank=True, default='',
        help_text="What this Setting governs — human-readable description of purpose and parent_model relationship",
    )
    paths = models.JSONField(
        default=dict, blank=True,
        help_text="Pointers to supporting documentation, schema files, pages, and related code",
    )

    class Meta:
        db_table = 'settings'
        constraints = [
            models.UniqueConstraint(
                fields=['parent_model', 'purpose'],
                condition=(
                    Q(purpose='wc:list_column_config')
                    & Q(is_active=True)
                    & Q(parent_model__isnull=False)
                    & ~Q(parent_model='')
                ),
                name='uniq_active_list_column_config_parent_model',
            ),
        ]

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
    
    # ── WALL: Settings are NEVER bulk-modified ──
    # These records represent days of careful refinement — layouts, behaviors,
    # selectlists, schema maps. Any automated process that wants to modify
    # Setting.config must set _setting_update_authorized = True on the instance
    # before calling save(). Without this flag, config changes are rejected.
    _setting_update_authorized = False

    def save(self, *args, **kwargs):
        """Ensure parent_model is normalized/validated even when created directly.

        Django doesn't call clean() automatically on save. We enforce it here so
        records created via ORM (bypassing serializers) still store canonical parent_model.
        """
        # Guard: block unauthorized config changes on existing records
        if self.pk and not self._setting_update_authorized:
            update_fields = kwargs.get('update_fields')
            if update_fields and 'config' in update_fields:
                # Check if config actually changed
                try:
                    orig = Setting.objects.filter(pk=self.pk).values_list('config', flat=True).first()
                    if orig is not None and orig != self.config:
                        import logging
                        logger = logging.getLogger('setting')
                        logger.warning(
                            'BLOCKED: unauthorized config change on Setting #%s (%s). '
                            'Set _setting_update_authorized=True to proceed.',
                            self.pk, self.name or self.ida,
                        )
                        raise ValidationError(
                            'Setting.config changes require explicit authorization. '
                            'Set record._setting_update_authorized = True before save().'
                        )
                except Setting.DoesNotExist:
                    pass

        # Use full_clean to include clean() and field validation
        try:
            self.full_clean()
        except ValidationError:
            raise

        result = super().save(*args, **kwargs)
        # Reset flag after save
        self._setting_update_authorized = False
        return result
    
    # Treat "comment" as a virtual field backed by data["comment"]
    @property
    def comment(self) -> str:
        d = getattr(self, "config", {}) or {}
        return str(d.get("comment") or "")

    @comment.setter
    def comment(self, value: str) -> None:
        d = dict(getattr(self, "config", {}) or {})
        d["comment"] = "" if value is None else str(value)
        self.config = d

#QQQ look at documents as a model
# we have settings record for each table that
# lists the fields that are denormalized into .refs.keywords.
# settings.parent_model = canonical model name and settings.purpose = wc:keywords
# settings.config contains an object listing fields
# for the values to be denormalized into keywords.

# Purposes registry (see readmes/settings.md for shapes):
# - view_edit: per-table field visibility/edit matrix by role
# - constants: global user-defined constants map
# - db_defaults: global database/platform defaults
# - sales_defaults: sales module defaults (global or per table)
# - purchase_defaults: purchasing module defaults (global or per table)
# - accounting_defaults: accounting/GL/tax defaults

#Logic now:
# Reads active Setting with purpose='wc:keywords' for the documents table.
# Accepts config.fields (list/tuple) or comma string (config.field_list fallback).
# On create: always enqueue (unless duplicate unprocessed Pending exists).
# On update: only enqueue if any tracked keyword field actually changed.
# Debounce: skips creating a new Pending if an unprocessed one already exists for the same table/record.
# Fallback: if no tracked fields configured but table in get_keyword_requirements(), only enqueue on create.
# Includes tracked_fields list in Pending.config for transparency.
# Guarded against errors; won’t break saves.

