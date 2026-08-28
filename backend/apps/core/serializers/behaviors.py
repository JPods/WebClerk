"""Shared serializer behaviors for cross-model linkage.

Standalone validator functions that any serializer calls. The serializer stays
thin — it validates input and calls these functions. Business logic stays in
services. Validation logic stays here.

These behaviors handle the universal patterns:
- Contact assignment (Action, Touch, OrgBase, Transaction headers)
- Org assignment (Action, Touch, Transaction headers)
- Project assignment (Action)
- Status transitions (any model with a status field)
- refs.links denormalization validation

For transaction-specific behaviors (customer != vendor, commission, totals),
see apps/transactions/serializers/behaviors.py.
"""

from rest_framework import serializers


# ── Contact linkage ──────────────────────────────────────────────────

def validate_contact_id(value):
    """Validate a contact_id FK on any model.

    Used by: Action, Touch, OrgBase, Transaction headers.
    Accepts int (BigIntegerField) or model instance (ForeignKey).
    Rejects non-positive values. Verifies contact exists and is active.
    """
    if value is None:
        return value
    # Handle model instance (DRF PrimaryKeyRelatedField resolves FK to object)
    pk = getattr(value, 'pk', value)
    if isinstance(pk, (int, float)) and pk <= 0:
        return None
    # If it's already a model instance, check is_active directly
    if hasattr(value, 'is_active'):
        if not value.is_active:
            raise serializers.ValidationError("Contact is inactive.")
        return value
    from apps.core.models.contact import Contact
    if not Contact.objects.filter(pk=pk, is_active=True).exists():
        raise serializers.ValidationError(f"Contact {pk} not found or inactive.")
    return value


# ── Org linkage ──────────────────────────────────────────────────────

def validate_org_id(value, org_model=None):
    """Validate an org_id FK on any model.

    Used by: Touch, Action (via customer/vendor), Transaction headers.
    Rejects non-positive values. Verifies org exists.
    """
    if value is None:
        return value
    if isinstance(value, (int, float)) and value <= 0:
        return None
    from apps.orgs.models.base import OrgBase
    qs = OrgBase.objects.filter(pk=value, is_active=True)
    if org_model:
        qs = qs.filter(org_type=org_model)
    if not qs.exists():
        label = f" ({org_model})" if org_model else ""
        raise serializers.ValidationError(f"Organization{label} {value} not found or inactive.")
    return value


def validate_customer_id(value):
    """Validate customer_id — delegates to validate_org_id."""
    return validate_org_id(value, org_model='customer')


def validate_vendor_id(value):
    """Validate vendor_id — delegates to validate_org_id."""
    return validate_org_id(value, org_model='vendor')


def validate_manufacturer_id(value):
    """Validate manufacturer_id — delegates to validate_org_id."""
    return validate_org_id(value, org_model='manufacturer')


def validate_customer_vendor_different(data):
    """Cross-field: customer and vendor must differ.

    Call from serializer.validate():
        def validate(self, data):
            validate_customer_vendor_different(data)
            return data
    """
    cid = data.get('customer_id')
    vid = data.get('vendor_id')
    if cid and vid and cid == vid:
        raise serializers.ValidationError(
            {"vendor_id": "Vendor cannot be the same as customer."}
        )


# ── Project linkage ──────────────────────────────────────────────────

def validate_project_id(value):
    """Validate project_id on Action or any model with a project FK.

    Rejects non-positive values. Verifies project exists and is active.
    """
    if value is None:
        return value
    if isinstance(value, (int, float)) and value <= 0:
        return None
    from apps.transactions.models.project import Project
    if not Project.objects.filter(pk=value, is_active=True).exists():
        raise serializers.ValidationError(f"Project {value} not found or inactive.")
    return value


# ── Status transitions ──────────────────────────────────────────────

def validate_status_transition(instance, new_status):
    """Validate status transition using the centralized service.

    Works for any model registered in validate_status.TRANSITIONS.
    Call from serializer:
        def validate_status(self, value):
            if self.instance:
                validate_status_transition(self.instance, value)
            return value
    """
    if not instance:
        return
    if instance.status == new_status:
        return  # no-op transition
    from apps.transactions.services.validate_status import validate_transition
    result = validate_transition(
        instance=instance,
        model_type=instance._meta.model_name,
        to_status=new_status,
    )
    if hasattr(result, 'can_proceed') and not result.can_proceed:
        errors = getattr(result, 'errors', ['Status transition not allowed'])
        raise serializers.ValidationError(errors[0] if errors else 'Status transition not allowed')


# ── refs.links helpers ───────────────────────────────────────────────

def name_from_refs(record, role):
    """Read a display name from refs.links.<role>.display_name.

    Falls back to empty string. Used by serializers to display
    linked record names without N+1 queries.
    """
    refs = getattr(record, 'refs', None)
    if not isinstance(refs, dict):
        return ""
    links = refs.get('links', {})
    if not isinstance(links, dict):
        return ""
    role_data = links.get(role, {})
    if not isinstance(role_data, dict):
        return ""
    return role_data.get('display_name', '') or role_data.get('company', '') or ""
