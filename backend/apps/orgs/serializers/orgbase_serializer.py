from rest_framework import serializers

from apps.orgs.models import OrgBase, Employee, Manufacturer, Rep, Vendor
from apps.core.serializers.behaviors import (
    validate_contact_id as _validate_contact_id,
    validate_status_transition,
)


class OrgBaseSerializer(serializers.ModelSerializer):
    """Serializer for OrgBase with company/display_name aliasing.

    PJPV: financial JSON envelope travels intact. No flattening.
    React reads financial.common.*, financial.customer.*, etc. by path.
    Validation delegates to core.serializers.behaviors.
    """

    company = serializers.CharField(source="display_name", required=False, allow_blank=True)
    display_name = serializers.SerializerMethodField()
    # FK-first: terms_fk is the model field; expose as terms_id in API.
    terms_id = serializers.IntegerField(source="terms_fk_id", required=False, allow_null=True)

    def get_display_name(self, obj):
        return getattr(obj, "display_name", "")

    def to_internal_value(self, data):
        if isinstance(data, dict) and "display_name" in data and "company" not in data:
            data = {**data, "company": data.get("display_name")}
        return super().to_internal_value(data)

    def validate_contact_id(self, value):
        """Validate primary contact FK — shared behavior."""
        return _validate_contact_id(value)

    def validate_status(self, value):
        """Validate status transition — shared behavior."""
        if self.instance:
            validate_status_transition(self.instance, value)
        return value

    class Meta:
        model = OrgBase
        fields = [
            "id",
            "org_type",
            "company",
            "display_name",
            "status",
            "is_active",
            "contact_id",
            "attention",
            "address_full",
            "email",
            "phone",
            "price_level",
            "terms",
            "terms_id",
            "contacts",
            "addresses",
            "phones",
            "emails",
            "domains",
            "relations",
            "financial",
            "docs",
            "connections",
            "config",
            "metrics",
            "gl_accounts",
            "refs",
            "prefs",
            "metadata",
            "dt_created",
            "dt_modified",
            "version",
        ]
        read_only_fields = ["id", "dt_created", "dt_modified", "version"]


class VendorSerializer(OrgBaseSerializer):
    """Vendor serializer — financial envelope intact (PJPV)."""
    class Meta(OrgBaseSerializer.Meta):
        model = Vendor


class RepSerializer(OrgBaseSerializer):
    """Rep serializer — financial envelope intact (PJPV)."""
    class Meta(OrgBaseSerializer.Meta):
        model = Rep


class EmployeeSerializer(OrgBaseSerializer):
    """Employee serializer — financial envelope intact (PJPV)."""
    class Meta(OrgBaseSerializer.Meta):
        model = Employee


class ManufacturerSerializer(OrgBaseSerializer):
    """Manufacturer serializer — financial envelope intact (PJPV)."""
    class Meta(OrgBaseSerializer.Meta):
        model = Manufacturer
