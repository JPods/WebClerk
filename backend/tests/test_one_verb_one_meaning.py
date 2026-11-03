"""One command name, one meaning, on every model.

Found 2026-11-03 (wc3-layouts browser walk): edit_hold registered 'release' on every model
and inventory_allocate registered 'release' on item; the second won silently, so the item
form's hold/release pair called inventory release with no quantity and got a 500.
"""
import pytest
from django.utils.crypto import get_random_string

from apps.core.services.door import Actor, Refused
from apps.core.services.verbs import COMMANDS, register_command, run_command


@pytest.fixture
def admin(django_user_model):
    user = django_user_model.objects.create_user(
        email='admin-verbs@example.fake', password=get_random_string(20), role='admin',
        name_first='A', name_last='Dmin')
    return Actor(user=user, kind='user', source='wcapi')


@pytest.mark.django_db
def test_item_release_drops_the_edit_hold(admin, item):
    assert run_command(admin, 'hold', 'item', item.pk, {})['mine'] is True
    assert run_command(admin, 'release', 'item', item.pk, {}) == {'released': True}


@pytest.mark.django_db
def test_unallocate_without_a_quantity_is_refused_not_converted(admin, item):
    with pytest.raises(Refused) as e:
        run_command(admin, 'unallocate', 'item', item.pk, {})
    assert e.value.status == 400


def test_a_second_registration_of_a_verb_is_refused():
    assert ('item', 'release') in COMMANDS
    with pytest.raises(ValueError, match='one name, one meaning'):
        register_command('item', 'release', lambda ctx: None)
