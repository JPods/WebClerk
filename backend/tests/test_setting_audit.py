"""The Setting audit fixes (2026-10-28): S-1, S-4, S-5, S-8, S-10."""
import pytest
from django.core.exceptions import ValidationError

from apps.core.models import Setting
from tests.conftest import make_setting

pytestmark = pytest.mark.django_db


def test_code_changes_a_setting_without_a_flag():
    """S-1: the door authorizes changes; the model keeps no second, bypassable guard."""
    s = make_setting(purpose='wc:system', name='s1', config={'v': 1})
    s.config = {'v': 2}
    s.save(update_fields=['config'])
    s.refresh_from_db()
    assert s.config == {'v': 2}


def test_creating_or_deleting_a_setting_still_needs_its_flag():
    with pytest.raises(ValidationError):
        Setting(purpose='wc:system', name='unflagged').save()
    s = make_setting(purpose='wc:system', name='kept')
    with pytest.raises(ValidationError):
        s.delete()
    assert Setting.objects.filter(pk=s.pk).exists()


def test_another_process_change_reaches_the_access_cache(monkeypatch):
    """S-4: a change this process never saw (another worker, a migration) is read on the next
    check, without a restart."""
    from apps.core.services import access
    Setting.objects.filter(purpose='wc:model', parent_model='customer').delete()
    make_setting(purpose='wc:model', parent_model='customer', name='customer',
                 config={'access': {'roles': {'sales': {'view': ['id'], 'edit': [], 'scope': {},
                                                        'create': False, 'delete': False}}}})
    access.clear_cache()
    assert access.model_access('customer')['sales']['view'] == ['id']
    # What another worker does: the row changes, this process gets no signal.
    Setting.objects.filter(purpose='wc:model', parent_model='customer').update(
        config={'access': {'roles': {'sales': {'view': ['id', 'company'], 'edit': [], 'scope': {},
                                               'create': False, 'delete': False}}}})
    assert access.model_access('customer')['sales']['view'] == ['id']      # within the window
    from apps.core.services import definition
    monkeypatch.setattr(definition, 'REVALIDATE_S', 0)
    assert access.model_access('customer')['sales']['view'] == ['id', 'company']


def test_one_model_definition_per_model():
    """S-5: a second active wc:model for a model would be silently ignored, so it is refused."""
    Setting.objects.filter(purpose='wc:model', parent_model='customer').delete()
    make_setting(purpose='wc:model', parent_model='customer', name='customer')
    with pytest.raises(ValidationError, match='uniq_active_wc_model_parent_model'):
        make_setting(purpose='wc:model', parent_model='customer', name='customer again')


def test_flush_makes_its_signal_on_a_fresh_database():
    """S-8: wc-flush is created with the create authorization, then bumped."""
    from apps.core.services.frontend_flush import flush_frontend
    Setting.objects.filter(ida='wc-flush').delete()
    first = flush_frontend()
    assert first['created'] and Setting.objects.filter(ida='wc-flush').exists()
    second = flush_frontend()
    assert not second['created']
    assert Setting.objects.get(ida='wc-flush').config == {'dt_changed': second['dt_changed']}


def test_a_seed_creates_then_updates_its_setting():
    """S-10: seed commands create their Setting on purpose (they were refused on create)."""
    s, created = Setting.authorized_update_or_create(
        ida='zz-seed', defaults={'name': 'seed', 'purpose': 'wc:system', 'config': {'v': 1}})
    assert created and s.config == {'v': 1}
    s, created = Setting.authorized_update_or_create(
        ida='zz-seed', defaults={'name': 'seed', 'purpose': 'wc:system', 'config': {'v': 2}})
    assert not created and Setting.objects.get(ida='zz-seed').config == {'v': 2}
    s, created = Setting.authorized_get_or_create(ida='zz-seed', defaults={'config': {'v': 3}})
    assert not created and s.config == {'v': 2}
