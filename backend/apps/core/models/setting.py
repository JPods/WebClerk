from django.db import models
from django.db.models import Q
from common.models import BaseModel
from django.core.exceptions import ValidationError
from apps.core.choices import SETTING_SCOPE_CHOICES
from apps.core.constants.model_registry import VALID_MODEL_NAMES, get_model_meta, get_model_meta_by_endpoint


class Setting(BaseModel):
    """Configuration record — stores layouts, defaults, field access, and behavior rules:
    the structure of the application, not its data (Bill, 2026-10-28)."""
    # config is as big as its users need — layouts and access lists grow with use
    # (Bill, 2026-10-24); the 2 MB request limit is the only ceiling.
    json_cap_overrides = {'config': None}
    json_depth_overrides = {'config': 16}

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
        # One model definition per model: access.py, journalize and the browser read the
        # first wc:model row for a model, so a second one would be silently ignored.
        constraints = [
            models.UniqueConstraint(
                fields=['parent_model', 'purpose'],
                condition=(
                    Q(purpose='wc:model')
                    & Q(is_active=True)
                    & Q(parent_model__isnull=False)
                    & ~Q(parent_model='')
                ),
                name='uniq_active_wc_model_parent_model',
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
    
    # ── WALL: Settings define how the application is built ──
    # Creating or deleting one is deliberate: code must set the flag first, or the
    # operation is rejected with a ValidationError.
    #   _setting_create_authorized = True  (creating new records)
    #   _setting_delete_authorized = True  (deleting records)
    # Changing one is the door's to authorize (SettingBehaviour, a superuser only);
    # there is no second guard here (Setting audit S-1, 2026-10-28). Migrations write
    # Settings with queryset.update(), which skips save() and its checks: fine in a
    # migration, never in a service.
    _setting_create_authorized = False
    _setting_delete_authorized = False

    def save(self, *args, **kwargs):
        """Ensure parent_model is normalized/validated even when created directly.

        Django doesn't call clean() automatically on save. We enforce it here so
        records created via ORM (bypassing serializers) still store canonical parent_model.
        """
        import logging
        logger = logging.getLogger('setting')

        # Guard: block unauthorized creation of new records
        if not self.pk and not self._setting_create_authorized:
            logger.warning(
                'BLOCKED: unauthorized Setting creation (%s, purpose=%s). '
                'Set _setting_create_authorized=True to proceed.',
                self.name or '(unnamed)', self.purpose or '(none)',
            )
            raise ValidationError(
                'Creating new Setting records requires explicit authorization. '
                'Set record._setting_create_authorized = True before save().'
            )

        # Use full_clean to include clean() and field validation
        try:
            self.full_clean()
        except ValidationError:
            raise

        # Company GL role map and commission accounts must name chart accounts.
        if self.purpose == 'wc:company_profile' and isinstance(self.config, dict):
            from apps.accounts.services.chart import validate_gl_map
            gl_defaults = {k: v for k, v in (self.config.get('gl_defaults') or {}).items() if k != 'note'}
            validate_gl_map(gl_defaults, owner='company gl_defaults')
            validate_gl_map((self.config.get('commission') or {}).get('gl_accounts'), owner='company commission.gl_accounts')
            from common.ida import validate_sequences
            try:
                validate_sequences(self.config.get('sequences'))
            except ValueError as e:              # a format that cannot make unique idas
                raise ValidationError(str(e))

        result = super().save(*args, **kwargs)
        self._setting_create_authorized = False
        return result

    def delete(self, *args, **kwargs):
        """Block unauthorized deletion of Setting records."""
        if not self._setting_delete_authorized:
            import logging
            logger = logging.getLogger('setting')
            logger.warning(
                'BLOCKED: unauthorized deletion of Setting #%s (%s, purpose=%s). '
                'Set _setting_delete_authorized=True to proceed.',
                self.pk, self.name or self.ida, self.purpose or '(none)',
            )
            raise ValidationError(
                'Deleting Setting records requires explicit authorization. '
                'Set record._setting_delete_authorized = True before delete().'
            )
        return super().delete(*args, **kwargs)

    @classmethod
    def authorized_create(cls, **kwargs):
        """Create a new Setting with explicit authorization."""
        obj = cls(**kwargs)
        obj._setting_create_authorized = True
        obj.save()
        return obj

    @classmethod
    def authorized_get_or_create(cls, defaults=None, **lookup):
        """get_or_create for a seed or command that creates its Setting on purpose."""
        obj = cls.objects.filter(**lookup).first()
        if obj is not None:
            return obj, False
        return cls.authorized_create(**lookup, **(defaults or {})), True

    @classmethod
    def authorized_update_or_create(cls, defaults=None, **lookup):
        """update_or_create for a seed or command that creates its Setting on purpose."""
        obj, created = cls.authorized_get_or_create(defaults=defaults, **lookup)
        if not created and defaults:
            for field, value in defaults.items():
                setattr(obj, field, value)
            obj.save()
        return obj, created

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


