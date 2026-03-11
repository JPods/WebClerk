from __future__ import annotations

from django.core.exceptions import FieldDoesNotExist


class SchemaLabelsAdminMixin:
    """Use model field names as labels in Django admin list and detail views."""

    def formfield_for_dbfield(self, db_field, request, **kwargs):  # type: ignore[override]
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)
        if formfield is not None:
            formfield.label = db_field.name
        return formfield

    def get_list_display(self, request):  # type: ignore[override]
        list_display = super().get_list_display(request)
        resolved = []
        for item in list_display:
            if isinstance(item, str) and self._is_plain_model_field(item):
                resolved.append(self._get_schema_list_callable(item))
            else:
                resolved.append(item)
        return tuple(resolved)

    def _is_plain_model_field(self, name: str) -> bool:
        try:
            self.model._meta.get_field(name)
        except FieldDoesNotExist:
            return False
        # If a custom method/property with this exact name exists, keep it.
        return not hasattr(self.__class__, name)

    def _get_schema_list_callable(self, field_name: str):
        cache_name = f"_schema_label_{field_name}"
        cached = getattr(self.__class__, cache_name, None)
        if cached is not None:
            return cached

        def _field_value(obj, _field_name=field_name):
            return getattr(obj, _field_name)

        _field_value.__name__ = cache_name
        _field_value.short_description = field_name
        _field_value.admin_order_field = field_name
        setattr(self.__class__, cache_name, _field_value)
        return _field_value
