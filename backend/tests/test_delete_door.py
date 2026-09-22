"""The delete door, and Django admin on it.

Bill, 2026-09-22: "Having every save, get, delete flow through their own individual
channel creates a maintainable system. There are few places to audit." And: everything
flows through the door including admin — no staff backdoor.
"""
import pytest
from django.contrib import admin

from apps.core.services.delete import delete_record
from apps.core.services.door import Actor, Refused
from apps.core.services.save import save_record

pytestmark = pytest.mark.django_db


def _item(ida: str, name: str = 'Deletable'):
    return save_record(Actor.system(), {'model_name': 'item', 'name': name, 'ida': ida})


def test_a_system_actor_deletes_without_a_request():
    from apps.products.models import Item
    made = _item('zz-del-1')

    result = delete_record(Actor.system(source='command'), 'item', made.obj_id)

    assert result.deleted is True and result.obj_id == made.obj_id
    assert not Item.objects.filter(pk=made.obj_id).exists()


def test_deleting_something_that_is_not_there_says_so_rather_than_failing():
    result = delete_record(Actor.system(), 'item', 99999999)
    assert result.deleted is False


def test_an_unknown_model_is_refused_with_its_code():
    with pytest.raises(Refused) as caught:
        delete_record(Actor.system(), 'notathing', 1)
    assert caught.value.code == 'unknown_model'


def test_a_missing_id_is_refused_as_an_invalid_payload():
    with pytest.raises(Refused) as caught:
        delete_record(Actor.system(), 'item', None)
    assert caught.value.status == 400 and caught.value.code == 'invalid_payload'


def test_a_guard_refusing_comes_back_as_coaching_not_a_crash():
    """The hard-delete rule, the cash door and a model's own delete() all refuse by
    raising. The door turns that into a Refused carrying the guard's own words."""
    from apps.products.models import Item

    made = _item('zz-del-guard')

    def _refuse(self, *args, **kwargs):
        raise RuntimeError('This item has been sold; retire it instead.')

    original = Item.delete
    Item.delete = _refuse
    try:
        with pytest.raises(Refused) as caught:
            delete_record(Actor.system(), 'item', made.obj_id)
    finally:
        Item.delete = original

    assert caught.value.status == 409 and caught.value.code == 'delete_refused'
    assert 'retire it instead' in caught.value.message
    assert Item.objects.filter(pk=made.obj_id).exists(), "a refused delete removes nothing"


# ── admin is on the door ──────────────────────────────────────────────

def test_every_registered_admin_is_on_the_door():
    """install() runs at startup and wraps every ModelAdmin, so an admin class written
    later cannot opt out by being written without the mixin."""
    from apps.core.admin_door import WcAdminMixin

    registry = admin.site._registry
    assert registry, "no admin classes registered — the check would pass vacuously"
    not_on_door = [model._meta.label for model, ma in registry.items()
                   if not isinstance(ma, WcAdminMixin)]
    assert not not_on_door, f"these admins still bypass the door: {not_on_door}"


def test_admin_save_goes_through_the_door(rf):
    """A ModelAdmin save writes through save_record, so an admin edit gets the field
    policy, validation, hooks and version check it never had."""
    from apps.core.admin_door import WcAdminMixin
    from apps.products.models import Item

    model_admin = admin.site._registry.get(Item)
    if model_admin is None:
        pytest.skip('Item is not registered in admin')
    assert isinstance(model_admin, WcAdminMixin)

    seen = {}
    import apps.core.admin_door as door_module
    original = door_module.save_record

    def _spy(actor, data, **kwargs):
        seen['actor'] = actor
        seen['data'] = data
        return original(actor, data, **kwargs)

    door_module.save_record = _spy
    try:
        request = rf.post('/admin/')
        request.user = None

        class _Form:
            cleaned_data = {'name': 'From Admin', 'ida': 'zz-del-admin'}

        obj = Item(name='From Admin', ida='zz-del-admin')
        model_admin.save_model(request, obj, _Form(), change=False)
    finally:
        door_module.save_record = original

    assert seen['actor'].kind == 'staff' and seen['actor'].source == 'admin'
    assert seen['data']['model_name'] == 'item'
    assert Item.objects.filter(ida='zz-del-admin').exists()


def test_a_staff_actor_is_a_person_and_meets_the_guards():
    """The bug this catches: admin_door built Actor(kind='staff'), and _authorize
    returned early for any kind that was not 'user'. So an admin save skipped the edit
    filters, the write policy and the contact guard — a staff backdoor, by accident,
    inside the change that was meant to close them (found by allie-36's audit,
    2026-09-22)."""
    from apps.core.services.door import Actor

    assert Actor(kind='staff').is_person is True
    assert Actor(kind='user').is_person is True
    assert Actor.system().is_person is False
    assert Actor(kind='sync').is_person is False
