import inspect
import pytest
from apps.transactions.services import flow
from apps.transactions.models import OrderLine

@pytest.mark.django_db
def test_line_copy_field_parity():
    """Ensure every JSON-ish field on OrderLine is considered in copy list.

    This guards the review process: when new JSON fields are added to BaseLineModel
    (and thus appear on concrete line models), they must be appended to
    flow.LINE_JSON_FIELDS_TO_COPY. Scalar fields are ignored.
    """
    # Representative instance (not saved) just to introspect _meta
    model = OrderLine()
    json_field_names = []
    for f in model._meta.get_fields():  # type: ignore[attr-defined]
        # We only care about JSONField declared directly on line models; heuristic: internal_type == 'JSONField'
        try:
            if getattr(f, 'get_internal_type', None) and f.get_internal_type() == 'JSONField':
                json_field_names.append(f.name)
        except Exception:
            continue

    missing = sorted(set(json_field_names) - set(flow.LINE_JSON_FIELDS_TO_COPY))
    assert not missing, f"New JSON line fields not in LINE_JSON_FIELDS_TO_COPY: {missing}. Update the constant in flow.py to include them."

    # Also ensure constant doesn't reference totally unknown fields (typos)
    unknown = sorted(set(flow.LINE_JSON_FIELDS_TO_COPY) - set(json_field_names))
    # We allow forward-looking fields (metadata, refs, prefs) that may be absent; document exceptions here.
    allowed_forward = {'metadata', 'refs', 'prefs'}
    real_unknown = [f for f in unknown if f not in allowed_forward]
    assert not real_unknown, f"LINE_JSON_FIELDS_TO_COPY contains unknown/typo fields: {real_unknown}"
