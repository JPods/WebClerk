import pytest
from django.utils import timezone
from apps.core.models import Contact
from common.models import VersionConflictError

@pytest.mark.django_db
def test_expected_version_conflict():
    c = Contact.objects.create(email='v@test.com', name_first='V', name_last='User')
    v = c.version
    # external update
    c2 = Contact.objects.get(pk=c.pk)
    c2.name_first = 'Other'
    c2.save()
    # stale save should raise
    c.name_last = 'Still'
    with pytest.raises(VersionConflictError):
        c.save(expected_version=v)

@pytest.mark.django_db
def test_changed_fields_recorded():
    c = Contact.objects.create(email='cf@test.com', name_first='C', name_last='F')
    c.name_first = 'Changed'
    v_before = c.version
    c.save(expected_version=v_before)
    meta = c.metadata
    changed = meta.get('versioning', {}).get('changed_fields')
    assert 'name_first' in changed
    universal = c.to_universal_dict()
    assert 'changed_fields' in universal and 'name_first' in universal['changed_fields']

@pytest.mark.django_db
def test_created_dt_immutable():
    c = Contact.objects.create(email='imm@test.com', name_first='Im', name_last='Mut')
    original = c.created_dt
    # If original somehow None (should not), set an arbitrary future value; else offset
    c.created_dt = (original + 999999) if original else int(timezone.now().timestamp() * 1000) + 999999
    v_before = c.version
    c.save(expected_version=v_before)
    assert c.created_dt == original

@pytest.mark.django_db
def test_touch_does_not_bump_version():
    c = Contact.objects.create(email='touch@test.com', name_first='To', name_last='Uch')
    v = c.version
    before_mod = c.modified_dt
    c.touch()
    c.refresh_from_db()
    assert c.version == v  # unchanged
    assert c.modified_dt >= before_mod
