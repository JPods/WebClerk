"""An org-role pointer looks up the role the field names.

Found 2026-11-03 (wc3-layouts browser walk): item.vendor and item.manufacturer searched
customers — every OrgBase FK was mapped to 'customer'. 17 lookups on 9 models.
"""
import pytest

from apps.core.services.field_behaviors import get_field_behaviors


@pytest.mark.django_db
@pytest.mark.parametrize('model_key,field,expected', [
    ('item', 'vendor', 'vendor'),
    ('item', 'manufacturer', 'manufacturer'),
    ('order', 'customer', 'customer'),
    ('contact', 'rep', 'rep'),
])
def test_org_role_fk_looks_up_its_own_model(model_key, field, expected):
    beh = get_field_behaviors(model_key)[field]
    assert beh['type'] == 'lookup'
    assert beh['model'] == expected
