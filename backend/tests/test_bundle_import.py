"""A bundle import keeps one record of itself, and its defects go to the system administrator
(Bill, 2026-10-29): company profile config.system_admin = {name, id}; a Bundle row whose status
is the folder its file sits in; one Log row; defects unresolved after three days become one
Action (Alice, escalate)."""
import uuid

import pytest
from django.core.exceptions import ValidationError
from django.utils.crypto import get_random_string

from apps.core.models import Action, Contact, Setting
from apps.core.models.log import Log
from apps.core.services import bundle_import, system_admin
from apps.sync.models.bundle import Bundle


def _profile():
    profile = Setting.objects.filter(purpose='wc:company_profile').first() or Setting(
        ida='company-profile', name='Company Profile', purpose='wc:company_profile',
        scope='system', config={})
    profile.config = {k: v for k, v in (profile.config or {}).items() if k != 'system_admin'}
    profile._setting_create_authorized = True
    profile.save()
    return profile


def _admin(first='Ada'):
    return Contact.objects.create(email=f'{get_random_string(8)}@example.com', name_first=first,
                                  name_last='Admin', role='admin', is_active=True)


@pytest.mark.django_db
def test_alice_names_the_first_admin_and_asks_every_admin():
    profile = _profile()
    _admin('Ada'), _admin('Bo')
    first = system_admin.admins().first()

    named = system_admin.current()

    assert named['id'] == first.id
    profile.refresh_from_db()
    assert profile.config['system_admin'] == named
    asks = Action.objects.filter(purpose=system_admin.ACTION_PURPOSE)
    assert sorted(asks.values_list('contact_id', flat=True)) == sorted(
        system_admin.admins().values_list('id', flat=True))
    assert Log.objects.filter(action='system_admin_named', record_id=profile.pk).count() == 1
    # Named once: reading it again asks nobody again.
    assert system_admin.current() == named and asks.count() == system_admin.admins().count()


@pytest.mark.django_db
def test_an_admin_no_longer_active_is_replaced():
    _profile()
    ada, bo = _admin('Ada'), _admin('Bo')
    profile = _profile()
    profile.config['system_admin'] = {'name': '', 'id': bo.id}
    profile.save()
    profile.refresh_from_db()
    assert profile.config['system_admin'] == {'name': 'Bo Admin', 'id': bo.id}   # name from the contact

    Contact.objects.filter(pk=bo.pk).update(is_active=False)
    assert system_admin.current()['id'] == system_admin.admins().first().id != bo.id


@pytest.mark.django_db
def test_the_company_cannot_name_someone_who_is_not_an_admin():
    profile = _profile()
    clerk = Contact.objects.create(email=f'{get_random_string(8)}@example.com', role='user')
    profile.config['system_admin'] = {'name': 'Clerk', 'id': clerk.id}
    with pytest.raises(ValidationError):
        profile.save()


@pytest.mark.django_db
def test_a_definition_matches_on_its_model_not_its_uuid(tmp_path, settings):
    settings.WORK_DIR = tmp_path
    mine = Setting.objects.filter(purpose='wc:model', parent_model='tag', is_active=True).first()
    if mine is None:
        mine = Setting(purpose='wc:model', parent_model='tag', name='tag')
        mine._setting_create_authorized = True
        mine.save()
    Setting.objects.filter(pk=mine.pk).update(config={'zz_mine': 1})
    theirs = {'uuid': str(uuid.uuid4()), 'purpose': 'wc:model', 'parent_model': 'tag',
              'name': 'tag', 'config': {'zz_mine': 2, 'zz_theirs': 1}}

    result = bundle_import.run('settings', {'settings': [theirs]}, source='test', load='settings')

    assert result['errors'] == [] and result['updated'] == 1
    mine.refresh_from_db()
    assert mine.config == {'zz_mine': 1, 'zz_theirs': 1}          # baseline merge: the company's value stands
    record = Bundle.objects.get(pk=result['bundle_id'])
    assert record.status == 'completed' and '/completed/' in record.config['payload_path']
    assert (tmp_path / record.config['payload_path']).exists()
    assert not Action.objects.filter(purpose=bundle_import.DEFECTS_PURPOSE).exists()


@pytest.mark.django_db
def test_defects_are_one_log_one_action_and_a_folder(tmp_path, settings):
    settings.WORK_DIR = tmp_path
    _profile()
    _admin()

    result = bundle_import.run('settings', {'settings': ['not a record', 'nor this']},
                               source='test', load='settings')

    record = Bundle.objects.get(pk=result['bundle_id'])
    assert record.status == 'defects' and len(record.response['defects']) == 2
    assert '/defects/' in record.config['payload_path']
    assert Log.objects.filter(action=bundle_import.PURPOSE, record_id=record.pk).count() == 1
    assert not Action.objects.filter(purpose=bundle_import.DEFECTS_PURPOSE).exists()   # the status flags it

    # Alice: not yet three days — nothing; past three days — one Action, once.
    day = 86_400_000
    assert bundle_import.escalate(now_ms=record.dt_processed + day) == []
    later = record.dt_processed + (bundle_import.ESCALATE_DAYS + 1) * day
    assert bundle_import.escalate(now_ms=later) == [record.pk]
    assert bundle_import.escalate(now_ms=later) == []
    told = Action.objects.get(purpose=bundle_import.DEFECTS_PURPOSE)
    assert told.contact_id == system_admin.current()['id']
    assert f'--rerun {record.pk}' in told.description['en']

    # Loaded again (nothing resolved): still defects, the file stays where it is.
    again = bundle_import.rerun(record.pk)
    record.refresh_from_db()
    assert again['bundle_id'] == record.pk and record.status == 'defects'
    assert (tmp_path / record.config['payload_path']).exists()
