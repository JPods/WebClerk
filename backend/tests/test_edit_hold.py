"""Edit holds (Bill, 2026-11-02): opening a record holds it for the company's edit delay; anyone
else is told who holds it and until when, and their save is refused; opening another record of the
model gives the first back. The version check stays underneath (test_wcapi_concurrency).
"""
import json
import secrets

import pytest
from django.core.cache import cache
from django.test import Client

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _clear_holds():
    cache.clear()
    yield
    cache.clear()


def _person(first):
    from apps.core.models import Contact
    user = Contact.objects.create_user(email=f'{first.lower()}@hold.test', password=secrets.token_urlsafe(16),
                                       name_first=first, name_last='Tester', username='', role='admin')
    client = Client()
    client.force_login(user)
    return client


def _command(client, verb, model, pk):
    r = client.post(f'/wcapi/{model}/{pk}/{verb}/', {}, content_type='application/json')
    assert r.status_code == 200, r.content
    return r.json()['data']['result']


def _save(client, model, pk, **fields):
    return client.put(f'/wcapi/{model}/{pk}/', json.dumps(fields), content_type='application/json')


def _contacts(n=2):
    from apps.core.models import Contact
    return [Contact.objects.create(email=f'target{i}@hold.test', name_first=f'T{i}') for i in range(n)]


def test_the_second_person_is_told_who_holds_it_and_cannot_save():
    ann, bob = _person('Ann'), _person('Bob')
    target, _ = _contacts()
    mine = _command(ann, 'hold', 'contact', target.pk)
    assert mine['mine'] is True and mine['minutes'] == 15
    theirs = _command(bob, 'hold', 'contact', target.pk)
    assert theirs['mine'] is False and theirs['held_by'] == 'Ann Tester' and theirs['until'].endswith('Z')

    refused = _save(bob, 'contact', target.pk, name_last='Bob was here')
    assert refused.status_code == 423
    assert refused.json()['error']['code'] == 'held'
    assert 'Ann Tester is editing' in refused.json()['message']
    assert _save(ann, 'contact', target.pk, name_last='Ann saved').status_code == 200


def test_opening_another_record_of_the_model_gives_the_first_back():
    ann, bob = _person('Ann'), _person('Bob')
    first, second = _contacts()
    _command(ann, 'hold', 'contact', first.pk)
    _command(ann, 'hold', 'contact', second.pk)
    assert _command(bob, 'hold', 'contact', first.pk)['mine'] is True
    assert _command(bob, 'hold', 'contact', second.pk)['mine'] is False


def test_release_and_running_out_open_the_record():
    from apps.core.services import edit_hold
    ann, bob = _person('Ann'), _person('Bob')
    target, other = _contacts()
    _command(ann, 'hold', 'contact', target.pk)
    assert _command(ann, 'release', 'contact', target.pk)['released'] is True
    assert _command(bob, 'hold', 'contact', target.pk)['mine'] is True

    _command(ann, 'hold', 'contact', other.pk)
    key = edit_hold._key('contact', other.pk)
    cache.set(key, {**cache.get(key), 'until': 0})               # the timer ran out
    assert _save(bob, 'contact', other.pk, name_last='after').status_code == 200


def test_the_edit_delay_is_the_companys_setting():
    from apps.core.models import Setting
    company = Setting.objects.get(purpose='wc:company_profile')
    company.config = {**company.config, 'edit_delay_minutes': 5}
    company._setting_create_authorized = True
    company.save()
    ann = _person('Ann')
    target, _ = _contacts()
    assert _command(ann, 'hold', 'contact', target.pk)['minutes'] == 5
