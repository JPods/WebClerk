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
