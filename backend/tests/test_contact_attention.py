"""Contact attention fills from the names only when empty (Bill, 2026-10-16).

An attention still equal to the stored names was derived, not typed, and follows the
names; one the user typed is theirs. The form applies the same rule
(frontend/src/utils/derivedFields.ts).
"""
import pytest

from apps.core.models import Contact

pytestmark = pytest.mark.django_db


def test_empty_attention_fills_from_names():
    c = Contact.objects.create(email='susy@example.com', name_first='Susy', name_last='Que')
    assert c.attention == 'Susy Que'


def test_derived_attention_follows_the_names():
    c = Contact.objects.create(email='susy@example.com', name_first='Susy')
    assert c.attention == 'Susy'
    c.name_last = 'Que'
    c.save()
    assert Contact.objects.get(pk=c.pk).attention == 'Susy Que'


def test_typed_attention_is_kept():
    c = Contact.objects.create(email='susy@example.com', name_first='Susy', name_last='Que',
                               attention='Ms. Que')
    assert c.attention == 'Ms. Que'
    c.name_first = 'Susan'
    c.save()
    assert Contact.objects.get(pk=c.pk).attention == 'Ms. Que'
