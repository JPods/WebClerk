import uuid
import pytest
from apps.products.models import Item

pytestmark = pytest.mark.django_db


def test_variant_canonical_and_uuid_and_parent_id():
    parent = Item.objects.create(name="Parent Tee", kind=Item.KIND_PHYSICAL)
    parent.set_variant_schema({"color": ["blue", "red"], "size": ["s", "m", "l"]})
    parent.save()

    child = Item.objects.create(name="Parent Tee Blue M", kind=Item.KIND_PHYSICAL)
    child.set_variant_attrs({"Color": "Blue", "size": "M"}, parent_uuid=str(parent.uuid), parent_id=parent.id)
    # canonical key normalized and sorted
    assert child.variant_canonical_key() == "color=blue|size=m"
    # parent id stored for local joins
    assert child.variant_parent_id() == parent.id
    # family set_uuid stable
    set_uuid_child = child.variant_set_uuid()
    assert set_uuid_child is not None
    # derived variant uuid is deterministic
    vu1 = child.variant_uuid()
    vu2 = child.variant_uuid()
    assert vu1 == vu2
    # changing order or case yields same canonical key -> same uuid
    child.set_variant_attrs({"size": "m", "COLOR": "BLUE"}, parent_uuid=str(parent.uuid), parent_id=parent.id)
    assert child.variant_canonical_key() == "color=blue|size=m"
    assert child.variant_uuid() == vu1


def test_variant_schema_validation():
    parent = Item.objects.create(name="Parent Shoe", kind=Item.KIND_PHYSICAL)
    parent.set_variant_schema({"color": ["black", "white"], "size": ["8", "9"]})
    parent.save()
    # invalid attribute value
    bad = Item(name="Bad Shoe", kind=Item.KIND_PHYSICAL)
    bad.set_variant_attrs({"color": "purple", "size": "9"}, parent_uuid=str(parent.uuid), parent_id=parent.id)
    with pytest.raises(Exception):
        # full_clean will raise ValidationError that bubbles up in tests
        bad.full_clean()
