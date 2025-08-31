import pytest
from django.utils import timezone

from common.tasks import recompute_relationship_counts, recompute_basic_stats
from apps.orgs.models.base_org_model import OrgBase, OrgType

@pytest.mark.django_db
def test_recompute_relationship_counts_updates_changed_orgs():
    # Org with empty relations should not be updated (no counts)
    o1 = OrgBase.objects.create(org_type=OrgType.CUSTOMER, display_name='Org One', status='active')
    # Org with relations will have counts populated
    o2 = OrgBase.objects.create(
        org_type=OrgType.VENDOR,
        display_name='Vendor Two',
        status='active',
        relations={
            'parents': [1,2],
            'children': [3],
            'linked_ids': [10,11,12]
        }
    )
    res = recompute_relationship_counts()
    assert res['processed'] >= 2
    assert res['updated'] >= 1
    o2.refresh_from_db()
    assert o2.relationship_stats['counts']['parents'] == 2
    assert o2.relationship_stats['counts']['children'] == 1
    assert o2.relationship_stats['counts']['linked'] == 3

@pytest.mark.django_db
def test_recompute_basic_stats_normalizes_structure():
    o = OrgBase.objects.create(org_type=OrgType.CUSTOMER, display_name='Org Three', status='active')
    # Force an invalid/malformed state by setting a scalar instead of dict
    OrgBase.objects.filter(pk=o.pk).update(stats=123)  # type: ignore[arg-type]
    res = recompute_basic_stats()
    assert res['processed'] >= 1
    o.refresh_from_db()
    assert isinstance(o.stats, dict)
    for key in ('counts','values','series','last'):
        assert key in o.stats

@pytest.mark.django_db
def test_atomic_append_alias_deprecated_but_functional():
    # Guard: atomic_append method should still exist (alias of atomic_list_append)
    o = OrgBase.objects.create(org_type=OrgType.CUSTOMER, display_name='Alias Org', status='active')
    v = o.version
    new_v = o.atomic_append('comments', ['notes'], {'text': 'alias note'}, expected_version=v)
    assert new_v == v + 1
    assert any(n.get('text') == 'alias note' for n in o.comments.get('notes', []))
