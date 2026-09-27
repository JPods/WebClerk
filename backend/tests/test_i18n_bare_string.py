"""A bare string for a translated field is stored in the user's language (Bill, 2026-09-26).

It was a 200 that stored nothing: the role filter keeps only enumerated leaves (action.en),
so a bare `action` string was dropped before the assignment could wrap it (allie-76).
"""
import pytest

from apps.core.models import Action

pytestmark = pytest.mark.django_db


def test_a_bare_string_lands_in_the_language_and_keeps_the_others(client, django_user_model):
    admin = django_user_model.objects.create_user(email='i18n-admin@test.com', password='x',
                                                  username='', role='admin')
    client.force_login(admin)
    action = Action.objects.create(action={'en': 'old', 'es': 'viejo'})
    r = client.put(f'/wcapi/action/{action.pk}/', {'action': 'Call Joe', 'version': action.version},
                   content_type='application/json')
    assert r.status_code == 200, r.content
    action.refresh_from_db()
    assert action.action == {'en': 'Call Joe', 'es': 'viejo'}


def test_a_plain_text_field_of_the_same_name_is_not_wrapped():
    """`description` is translated on an action and plain text on an item."""
    from apps.core.services.door import Actor
    from apps.core.services.save import save_record
    from apps.products.models import Item
    item = Item.objects.create(name='Plain')
    save_record(Actor.system(), {'model_name': 'item', 'id': item.pk, 'description': 'Just text'})
    item.refresh_from_db()
    assert item.description == 'Just text'


def test_it_lands_in_the_writers_language_from_their_prefs(client, django_user_model):
    admin = django_user_model.objects.create_user(email='i18n-es@test.com', password='x',
                                                  username='', role='admin')
    admin.prefs = {**(admin.prefs or {}), 'language': 'es'}
    admin.save(update_fields=['prefs'])
    client.force_login(admin)
    action = Action.objects.create(action={'en': 'Call Joe'})
    r = client.put(f'/wcapi/action/{action.pk}/', {'action': 'Llamar a Joe', 'version': action.version},
                   content_type='application/json')
    assert r.status_code == 200, r.content
    action.refresh_from_db()
    assert action.action == {'en': 'Call Joe', 'es': 'Llamar a Joe'}


def test_a_language_is_a_two_letter_code():
    from apps.core.models.contact_pydantic import ContactPrefs
    assert ContactPrefs(language='ES').language == 'es'
    assert ContactPrefs(language='').language is None
    with pytest.raises(ValueError, match='ISO 639-1'):
        ContactPrefs(language='eng')


def test_the_field_op_form_and_a_bad_stored_language(client, django_user_model):
    """{mode: update, value: '…'} is a bare string too; a stored language that is not a code
    (a dot-path write skips the envelope check) is never a translation key (Fable)."""
    admin = django_user_model.objects.create_user(email='i18n-op@test.com', password='x',
                                                  username='', role='admin')
    admin.prefs = {**(admin.prefs or {}), 'language': 'English'}
    admin.save(update_fields=['prefs'])
    client.force_login(admin)
    action = Action.objects.create(action={'en': 'old'})
    r = client.put(f'/wcapi/action/{action.pk}/',
                   {'action': {'mode': 'update', 'value': 'Call Joe'}, 'version': action.version},
                   content_type='application/json')
    assert r.status_code == 200, r.content
    action.refresh_from_db()
    assert action.action == {'en': 'Call Joe'}


def test_a_list_field_named_like_a_translation_is_not_wrapped():
    from apps.core.services.door import Actor
    from apps.core.services.save import _wrap_i18n
    assert _wrap_i18n(Action, {'languages': 'es'}, 'en') == {'languages': 'es'}
