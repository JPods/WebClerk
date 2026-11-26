"""A record's metadata.history names the person who made and last changed it.

MetadataMixin.save stamped history.created/modified.contact_id from created_by_id/modified_by_id,
attributes no model declares and no code set, so every record on wc_demo read 0 (found by the
allie-25 audit as "a convert leaves created.contact_id 0", 2026-11-25; it was every save). The door
knows who is acting (door.acting_actor, Bill 2026-10-28), as Log and Action already read it: the
stamp reads it. A record our own code saves inside a person's verb (a hook's action, a signoff)
names that person; outside any verb (a task, a command) the stamp stays 0.
"""
import pytest
from django.utils.crypto import get_random_string

from apps.core.services.door import Actor
from apps.core.services.verbs import run, run_command
from apps.orgs.models import OrgBase, Customer
from apps.transactions.models import Quote, QuoteLine, Order, OrderLine
from apps.transactions.services.convert.convert import convert_quote_to_order


@pytest.fixture(autouse=True)
def _no_pending_dispatch(monkeypatch):
    monkeypatch.setattr("apps.products.dispatch_pending.dispatch_pending_processing",
                        lambda *args, **kwargs: None)


@pytest.fixture
def person(django_user_model):
    return django_user_model.objects.create_superuser(
        email='stamp@example.com', password=get_random_string(20), name_first='S', name_last='P')


def _quote():
    customer = OrgBase.objects.create(company="Stamp Co", org_type="customer")
    quote = Quote.objects.create(status='active', customer_id=customer.id)
    QuoteLine.objects.create(quote=quote, item={'description': 'Item'},
                             price={'unit': 10.0, 'precision': 2}, cost={'unit': 6.0},
                             quantity={'active': 2, 'precision': 2})
    return quote


def _who(record, moment):
    record.refresh_from_db()
    return record.metadata['history'][moment]['contact_id']


@pytest.mark.django_db
def test_a_convert_names_the_person_on_the_new_document_and_its_lines(person):
    result = run_command(Actor(user=person), 'convert', 'quote', _quote().pk, {'to': 'order'})
    order = Order.objects.get(pk=result['order_id'])
    assert _who(order, 'created') == person.pk
    assert _who(order, 'modified') == person.pk
    lines = list(OrderLine.objects.filter(order=order))
    assert lines and all(_who(line, 'created') == person.pk for line in lines)


@pytest.mark.django_db
def test_a_save_through_the_door_names_who_made_it_and_who_changed_it(person, django_user_model):
    made = run(Actor(user=person), 'save', 'customer', {'company': 'Stamped Co'})
    org = Customer.objects.get(pk=made.obj_id)
    assert _who(org, 'created') == person.pk

    other = django_user_model.objects.create_superuser(
        email='stamp2@example.com', password=get_random_string(20), name_first='O', name_last='T')
    run(Actor(user=other), 'save', 'customer', {'id': org.pk, 'company': 'Restamped Co'})
    assert _who(org, 'created') == person.pk          # the maker stays
    assert _who(org, 'modified') == other.pk


@pytest.mark.django_db
def test_our_own_code_outside_a_verb_stamps_zero():
    result = convert_quote_to_order(_quote().pk)      # the system actor, no verb
    assert _who(Order.objects.get(pk=result['order_id']), 'created') == 0
