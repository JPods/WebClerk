"""Shared admin mixins for webClerk3."""
from django.db import models as dj_models


class ScalarFirstFieldsetMixin:
    """Dynamically build fieldsets: scalar fields alphabetically, then JSON/object fields.

    Include this mixin in any ModelAdmin that does not define explicit fieldsets.
    Classes that define their own fieldsets (e.g. OrgBaseAdmin) or use a
    domain-specific fieldset mixin (e.g. JSONBFieldsetMixin in transactions)
    should NOT add this mixin — their explicit ordering already satisfies the
    scalar-first convention.
    """

    readonly_auto_fields = ("id", "uuid", "dt_created", "dt_modified", "version")
    scalar_fieldset_title = "Scalar Fields"
    object_fieldset_title = "Object/JSON Fields"
    detail_order_override: tuple[str, ...] = ()

    def _apply_order_override(self, names, *, object_fields=False):
        override = tuple(getattr(self, "detail_order_override", ()) or ())
        if not override:
            return tuple(sorted(names))

        target = list(names)
        target_set = set(target)
        ordered = []
        for field_name in override:
            if field_name in target_set and field_name not in ordered:
                ordered.append(field_name)
        remaining = sorted(field_name for field_name in target if field_name not in ordered)
        return tuple(ordered + remaining)

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        for field_name in self.readonly_auto_fields:
            if hasattr(self.model, field_name) and field_name not in readonly:
                readonly.append(field_name)
        return tuple(readonly)

    def _get_scalar_fields(self):
        """Return scalar fields, honoring any explicit To_Alice ordering."""
        names = []
        for field in self.model._meta.fields:
            if isinstance(field, dj_models.JSONField):
                continue
            if isinstance(field, (dj_models.ForeignKey, dj_models.OneToOneField, dj_models.ManyToManyField)):
                continue
            names.append(field.name)
        return self._apply_order_override(names)

    def _get_object_fields(self):
        """Return JSON/FK fields, honoring any explicit To_Alice ordering."""
        names = []
        for field in self.model._meta.fields:
            if isinstance(field, dj_models.JSONField):
                names.append(field.name)
            elif isinstance(field, (dj_models.ForeignKey, dj_models.OneToOneField)):
                names.append(field.name)
        return self._apply_order_override(names, object_fields=True)

    def get_fieldsets(self, request, obj=None):
        scalar_fields = self._get_scalar_fields()
        object_fields = self._get_object_fields()
        fieldsets = []
        if scalar_fields:
            fieldsets.append((self.scalar_fieldset_title, {"fields": scalar_fields}))
        if object_fields:
            fieldsets.append((self.object_fieldset_title, {"fields": object_fields, "classes": ("collapse",)}))
        if fieldsets:
            return tuple(fieldsets)
        return super().get_fieldsets(request, obj)
