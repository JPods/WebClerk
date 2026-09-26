"""Fix #5 (Fable L3 H-2) — Bill, 2026-09-25: each ModelBehaviour declares the underscore
signals it reads. An action's _attachments reaches its hook for any person who may edit
actions; an undeclared signal is still refused with coaching."""
import pytest

from apps.core.models import Contact
from apps.core.services.door import Actor, Refused
from apps.core.services.save import save_record
from common.schemas.carrier import CarrierError, read_carrier
from tests.test_write_policy import _grant

pytestmark = pytest.mark.django_db

ACTION_BLOCK = {'view': ['@all'], 'edit': ['@all'], 'scope': {}, 'create': True}


def test_a_declared_signal_passes_and_is_type_checked():
    read_carrier({'_attachments': [1, 2]}, declared={'_attachments': list})
    with pytest.raises(CarrierError, match='expected list'):
        read_carrier({'_attachments': 'x'}, declared={'_attachments': list})


def test_an_undeclared_signal_is_refused_and_names_what_the_model_reads():
    with pytest.raises(CarrierError) as e:
        read_carrier({'_frobnicate': 1}, declared={'_attachments': list})
    assert '_attachments' in str(e.value)


def test_a_person_attaches_a_document_to_an_action():
    from apps.docs.models import Document, LinkageEntry
    _grant('action', 'employee', ACTION_BLOCK)
    person = Contact.objects.create(email='attach@example.com', role='employee')
    doc = Document.objects.create(name='spec.pdf')
    saved = save_record(Actor(user=person), {'model_name': 'action', 'action': {'en': 'Review spec'},
                                             '_attachments': [doc.pk]})
    assert LinkageEntry.objects.filter(model_name='action', record_id=saved.obj_id).exists()


def test_a_bogus_signal_on_an_action_is_still_refused():
    _grant('action', 'employee', ACTION_BLOCK)
    person = Contact.objects.create(email='bogus@example.com', role='employee')
    with pytest.raises((Refused, CarrierError)):
        save_record(Actor(user=person), {'model_name': 'action', 'action': {'en': 'x'}, '_bogus': 1})
