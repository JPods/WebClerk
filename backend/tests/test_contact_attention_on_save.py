"""Attention fills from the names on save (Bill, 2026-10-16; checked on the flight-simulator
walk 2026-11-03, where the form's own rule had been missing on TransactionDetail)."""
import pytest
from django.contrib.auth import get_user_model

from apps.core.models import Contact
from apps.core.services.door import Actor
from apps.core.services.save import save_record

User = get_user_model()
pytestmark = pytest.mark.django_db


def test_attention_fills_from_the_names_on_save():
    user = User.objects.create_superuser(email='att@example.com', password=None,
                                         name_first='At', name_last='Tention', username='')
    c = Contact.objects.create(email='new@test.com')
    save_record(Actor(user=user), {'name_first': 'Sally', 'name_last': 'Smith', 'version': c.version},
                model_key='contact', record_id=c.id)
    assert Contact.objects.get(pk=c.pk).attention == 'Sally Smith'
