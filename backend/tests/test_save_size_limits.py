"""Size limits refuse; they never drop.

A field over what one save may send used to be skipped while the save reported success:
a 59 KB layout came back "saved" and stored nothing (wc3, 2026-10-24). Now:
  - one save may send 15,000 bytes per field — over that, the save is refused;
  - a record's JSON field is capped (config 64 KB), checked before the write;
  - Setting config has neither cap and nests to 16: as big as its users need (Bill).
"""
import pytest
from django.contrib.auth import get_user_model

from apps.communications.models.domain import Domain
from apps.core.models.setting import Setting
from apps.core.services.door import Actor, Refused
from apps.core.services.save import save_record
from common.models import MAX_CONFIG_SIZE, MAX_SAVE_FIELD_SIZE, JsonTooLarge

User = get_user_model()


@pytest.fixture
def actor(db):
    user = User.objects.create_superuser(email='sizes@example.com', password=None,
                                         name_first='Size', name_last='Limits', username='')
    return Actor(user=user)


def _domain():
    return Domain.objects.create(path='https://sizes.example.com', type='website')


@pytest.mark.django_db
def test_a_field_over_one_save_is_refused_and_nothing_is_written(actor):
    d = _domain()
    with pytest.raises(Refused) as e:
        save_record(actor, {'config': {'blob': 'x' * (MAX_SAVE_FIELD_SIZE + 1)}, 'type': 'email'},
                    model_key='domain', record_id=d.id)
    assert e.value.status == 400 and e.value.code == 'field_refused'
    assert 'Send only the part that changed' in str(e.value.message)
    d.refresh_from_db()
    assert d.type == 'website', 'the other fields of a refused save are not written either'


@pytest.mark.django_db
def test_a_record_over_its_cap_is_refused_before_the_write():
    d = _domain()
    d.config = {'blob': 'x' * (MAX_CONFIG_SIZE + 1)}
    with pytest.raises(JsonTooLarge):
        d.save()
    d.refresh_from_db()
    assert 'blob' not in (d.config or {})


@pytest.mark.django_db
def test_setting_config_is_as_big_and_as_deep_as_its_users_need(actor):
    s = Setting(name='qqq size test', purpose='wc:test', scope='system')
    s._setting_create_authorized = True
    s.save()
    deep = {'a': {'b': {'c': {'d': [{'e': [{'f': {'g': [{'h': 1}]}}]}]}}}}   # 11 levels
    big = {'rows': ['x' * 1000 for _ in range(MAX_CONFIG_SIZE // 1000 + 10)]}  # over 64 KB
    save_record(actor, {'config': {**deep, **big}}, model_key='setting', record_id=s.id)
    s.refresh_from_db()
    assert s.config['a']['b']['c']['d'][0]['e'][0]['f']['g'][0]['h'] == 1
    assert len(s.config['rows']) == len(big['rows'])
