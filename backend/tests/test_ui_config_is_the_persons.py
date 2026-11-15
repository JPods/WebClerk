"""A person's interface settings are saved on their own Contact, never on a fixed one.

Found 2026-11-14 building a person's own form layout: save_ui_config wrote to contact 8
whenever the browser named no contact, and the browser never names one. wcapi/manage now
passes the signed-in person (_acting_user_id).
"""
import pytest
from django.utils.crypto import get_random_string

from apps.core.services.ui_config import get_ui_config, save_ui_config


def _person(django_user_model, n):
    return django_user_model.objects.create_user(
        email=f'ui{n}@example.fake', password=get_random_string(20), role='admin',
        name_first='U', name_last=str(n))


@pytest.mark.django_db
def test_a_form_layout_is_kept_for_the_person_who_saved_it(django_user_model):
    one, two = _person(django_user_model, 1), _person(django_user_model, 2)
    columns = [{'title': 'bill_to', 'weight': 1.3, 'fields': [{'field': 'terms', 'label': 'terms'}]}]
    assert save_ui_config({'form': {'quote': {'columns': columns}}}, one.pk)['saved'] is True
    assert get_ui_config(one.pk)['form']['quote']['columns'] == columns
    assert 'form' not in get_ui_config(two.pk)
    # Back to the company's form: the person's own is dropped.
    save_ui_config({'form': {'quote': None}}, one.pk)
    assert get_ui_config(one.pk)['form']['quote'] is None


@pytest.mark.django_db
def test_nothing_is_saved_when_no_one_is_signed_in():
    assert save_ui_config({'theme': {'active': 'light'}}, None)['saved'] is False


@pytest.mark.django_db
def test_manage_saves_for_the_signed_in_person(client, django_user_model):
    from rest_framework.test import APIClient
    one, two = _person(django_user_model, 3), _person(django_user_model, 4)
    api = APIClient()
    api.force_authenticate(one)
    # The browser names no contact; even a contact_id sent by the client does not win.
    r = api.post('/wcapi/_manage/', {'action': 'save_ui_config',
                                    'params': {'config_ui': {'detail': {'default_view': 'admin'}},
                                               'contact_id': two.pk}}, format='json')
    assert r.status_code == 200, r.content
    one.refresh_from_db(); two.refresh_from_db()
    assert (one.config or {}).get('ui', {}).get('detail', {}).get('default_view') == 'admin'
    assert 'ui' not in (two.config or {})
