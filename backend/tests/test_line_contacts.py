"""Line contacts (readme 109 P6; Bill, 2026-11-12): "a customer is a furniture store that buys a
warranty for one of their customers. The end contact would be listed [as] the
contacts.warranty_holder" — on the line's refs.contacts, on the serial the line issued, and the
contact lists the serial, the invoice and the invoice line. transactions/services/line_contacts.py.
"""
import secrets

import pytest
from rest_framework.test import APIClient

from apps.core.models import Contact
from apps.core.services import select_lists
from apps.core.services.door import Actor, Refused
from apps.core.services.save import save_record
from apps.orgs.models import OrgBase
from apps.products.models.serial import Serial
from apps.transactions.models import Invoice, InvoiceLine, Order, OrderLine, Quote, QuoteLine
from apps.transactions.services.convert.convert import convert_order_to_invoice, convert_quote_to_order

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _no_pending_dispatch(monkeypatch):
    monkeypatch.setattr("apps.products.dispatch_pending.dispatch_pending_processing",
                        lambda *args, **kwargs: None)


def _switch(model_key, on):
    """The document's switch as a staff member sets it in the Defaults console."""
    from apps.core.models import Setting
    from apps.core.services import definition
    s = Setting.objects.get(purpose='wc:model', parent_model=model_key)
    s.config = {**s.config, 'defaults': {**s.config['defaults'], 'features': {'line_contacts': on}}}
    s._setting_create_authorized = True
    s.save()
    definition.clear(model_key)


@pytest.fixture
def roles(model_defaults):
    select_lists.add_value('contact', 'transaction_role', 'warranty_holder', label='Warranty Holder')
    for model_key in ('quote', 'order', 'invoice'):
        _switch(model_key, True)


@pytest.fixture
def admin(django_user_model):
    return django_user_model.objects.create_superuser(
        email='linecontacts@example.com', password=None, name_first='Lin', name_last='Con', username='')


@pytest.fixture
def store():
    return OrgBase.objects.create(company='Fine Furniture Co', org_type='customer')


@pytest.fixture
def holder():
    return Contact.objects.create(email='pat.holder@example.com', name_first='Pat', name_last='Holder',
                                  company='Holder Household')


def _as(user, kind='user'):
    return Actor.system('command') if kind == 'system' else Actor(user=user, kind=kind, source='wcapi')


def _invoice(store, lines=1):
    inv = Invoice.objects.create(status='planned', customer_id=store.id, finance={'sales_tax_rate': 0})
    made = [InvoiceLine.objects.create(invoice=inv, item={'description': f'Sofa warranty {i}'},
                                       price={'unit': 100.0, 'precision': 2},
                                       quantity={'active': 1, 'precision': 2})
            for i in range(lines)]
    inv.refresh_from_db()
    return inv, made


def _name(admin, inv, line, people, kind='user'):
    inv.refresh_from_db()
    line.refresh_from_db()
    save_record(_as(admin, kind), {'id': inv.pk, 'version': inv.version, 'lines': [
        {'id': line.pk, 'version': line.version, 'refs': {'contacts': people},
         '_dirty': True}]}, model_key='invoice')
    line.refresh_from_db()
    return line


def _links(contact, key):
    contact.refresh_from_db()
    return sorted(int(r['id']) for r in ((contact.refs or {}).get('links') or {}).get(key) or [])


def test_a_line_names_its_warranty_holder_and_the_holder_lists_the_line_and_the_invoice(
        admin, roles, store, holder):
    inv, (line,) = _invoice(store)
    line = _name(admin, inv, line, [{'role': 'warranty_holder', 'contact_id': holder.pk}])
    assert line.refs['contacts'] == [{
        'role': 'warranty_holder', 'contact_id': holder.pk, 'display_name': 'Pat Holder',
        'company': 'Holder Household', 'email': 'pat.holder@example.com', 'phone': ''}]
    assert _links(holder, 'invoice_line') == [line.pk]
    assert _links(holder, 'invoice') == [inv.pk]


def test_the_form_reads_the_holder_on_the_wire(admin, roles, store, holder):
    """The wire, not the row (TFTS 2026-11-12): a leaf no access set names is projected out."""
    inv, (line,) = _invoice(store)
    _name(admin, inv, line, [{'role': 'warranty_holder', 'contact_id': holder.pk}])
    staff = Contact.objects.create_superuser(email='wire@example.com', password=secrets.token_urlsafe(16))
    client = APIClient()
    client.force_authenticate(staff)
    r = client.get(f'/wcapi/invoice/{inv.pk}/', HTTP_HOST='localhost')
    assert r.status_code == 200, r.content
    sent = r.json()['data']['record']['lines'][0]['refs']['contacts']
    assert sent[0]['role'] == 'warranty_holder' and sent[0]['contact_id'] == holder.pk
    assert sent[0]['display_name'] == 'Pat Holder'


def test_an_entry_keeps_what_it_copied_when_the_contact_changes(admin, roles, store, holder):
    inv, (line,) = _invoice(store)
    line = _name(admin, inv, line, [{'role': 'warranty_holder', 'contact_id': holder.pk}])
    Contact.objects.filter(pk=holder.pk).update(name_last='Moved')
    line = _name(admin, inv, line, line.refs['contacts'])
    assert line.refs['contacts'][0]['display_name'] == 'Pat Holder'


def test_taking_the_holder_off_the_line_takes_the_line_off_the_holder(admin, roles, store, holder):
    inv, (line,) = _invoice(store)
    line = _name(admin, inv, line, [{'role': 'warranty_holder', 'contact_id': holder.pk}])
    line = _name(admin, inv, line, [])
    assert line.refs['contacts'] == []
    assert _links(holder, 'invoice_line') == [] and _links(holder, 'invoice') == []


def test_the_holder_lists_the_invoice_while_any_of_its_lines_names_them(admin, roles, store, holder):
    inv, (a, b) = _invoice(store, lines=2)
    entry = [{'role': 'warranty_holder', 'contact_id': holder.pk}]
    _name(admin, inv, a, entry)
    _name(admin, inv, b, entry)
    assert _links(holder, 'invoice_line') == sorted([a.pk, b.pk])
    _name(admin, inv, a, [])
    assert _links(holder, 'invoice_line') == [b.pk] and _links(holder, 'invoice') == [inv.pk]


def test_deleting_the_line_takes_it_off_the_holder(admin, roles, store, holder):
    inv, (line,) = _invoice(store)
    _name(admin, inv, line, [{'role': 'warranty_holder', 'contact_id': holder.pk}])
    from tests.utils import save_document
    save_document('invoice', {'id': inv.pk}, [{'id': line.pk, '_delete': True}])
    assert not InvoiceLine.objects.filter(pk=line.pk).exists()
    assert _links(holder, 'invoice_line') == [] and _links(holder, 'invoice') == []


def test_a_person_is_asked_before_a_role_not_on_the_list_is_saved(admin, roles, store, holder):
    inv, (line,) = _invoice(store)
    with pytest.raises(Refused) as refused:
        _name(admin, inv, line, [{'role': 'installer', 'contact_id': holder.pk}])
    assert refused.value.code == 'value_not_listed'
    assert refused.value.details['unlisted'] == {'transaction_role': 'installer'}
    assert refused.value.details['may_add'] == {'transaction_role': True}
    select_lists.add_value('contact', 'transaction_role', 'installer', actor=_as(admin))
    line = _name(admin, inv, line, [{'role': 'installer', 'contact_id': holder.pk}])
    assert line.refs['contacts'][0]['role'] == 'installer'


def test_code_that_writes_an_unlisted_role_is_refused(admin, roles, store, holder):
    inv, (line,) = _invoice(store)
    with pytest.raises(Refused) as refused:
        _name(admin, inv, line, [{'role': 'warranty-holder', 'contact_id': holder.pk}], kind='system')
    assert refused.value.code == 'value_not_listed' and refused.value.details['may_add'] == {}


@pytest.mark.parametrize('entry, code', [
    ({'role': 'warranty_holder'}, 'line_contact_incomplete'),
    ({'contact_id': 1}, 'line_contact_incomplete'),
    ({'role': 'warranty_holder', 'contact_id': 10 ** 9}, 'line_contact_not_found'),
])
def test_an_entry_that_is_not_whole_is_refused_with_what_it_needs(admin, roles, store, entry, code):
    inv, (line,) = _invoice(store)
    with pytest.raises(Refused) as refused:
        _name(admin, inv, line, [entry])
    assert refused.value.code == code


def test_the_serial_the_line_issues_takes_the_holder_and_the_holder_lists_the_serial(
        admin, roles, store, holder):
    inv, (line,) = _invoice(store)
    line = _name(admin, inv, line, [{'role': 'warranty_holder', 'contact_id': holder.pk}])
    serial = Serial.objects.create(serial_ida='SN-P6-1', status='available')
    serial.issue_on_invoice(store.pk, inv.pk, sales_line_ref=line.pk)
    serial.refresh_from_db()
    assert serial.refs['contacts'] == line.refs['contacts']
    assert _links(holder, 'serial') == [serial.pk]


def test_a_holder_named_after_the_serial_was_issued_reaches_the_serial(admin, roles, store, holder):
    inv, (line,) = _invoice(store)
    serial = Serial.objects.create(serial_ida='SN-P6-2', status='available')
    serial.issue_on_invoice(store.pk, inv.pk, sales_line_ref=line.pk)
    line = _name(admin, inv, line, [{'role': 'warranty_holder', 'contact_id': holder.pk}])
    serial.refresh_from_db()
    assert serial.refs['contacts'] == line.refs['contacts']
    assert _links(holder, 'serial') == [serial.pk]


def test_a_serial_back_in_stock_is_held_by_nobody(admin, roles, store, holder):
    inv, (line,) = _invoice(store)
    line = _name(admin, inv, line, [{'role': 'warranty_holder', 'contact_id': holder.pk}])
    serial = Serial.objects.create(serial_ida='SN-P6-3', status='available')
    serial.issue_on_invoice(store.pk, inv.pk, sales_line_ref=line.pk)
    serial.make_available()
    serial.refresh_from_db()
    assert serial.refs['contacts'] == [] and _links(holder, 'serial') == []


def test_the_holder_goes_with_the_line_from_quote_to_order_to_invoice(roles, store, holder):
    quote = Quote.objects.create(status='active', customer_id=store.id)
    QuoteLine.objects.create(quote=quote, item={'description': 'Sofa warranty'},
                             price={'unit': 100.0, 'precision': 2}, cost={'unit': 60.0},
                             quantity={'active': 1, 'precision': 2},
                             refs={'contacts': [{'role': 'warranty_holder', 'contact_id': holder.pk}]})
    assert _links(holder, 'quote') == [quote.pk]

    order = Order.objects.get(pk=convert_quote_to_order(quote.pk)['order_id'])
    order_line = OrderLine.objects.get(order=order)
    assert order_line.refs['contacts'][0]['contact_id'] == holder.pk
    assert order_line.refs['contacts'][0]['display_name'] == 'Pat Holder'
    assert _links(holder, 'order_line') == [order_line.pk]

    invoice = Invoice.objects.get(pk=convert_order_to_invoice(order.pk)['invoice_id'])
    invoice_line = InvoiceLine.objects.get(invoice=invoice)
    assert invoice_line.refs['contacts'][0]['role'] == 'warranty_holder'
    assert _links(holder, 'invoice') == [invoice.pk]


def test_a_fresh_installation_has_line_contacts_turned_off(model_defaults):
    from apps.core.services.defaults import feature_on, shipped_defaults
    assert shipped_defaults('invoice')['features'] == {'line_contacts': False}
    assert 'features' not in shipped_defaults('purchase')
    assert not feature_on('invoice', 'line_contacts') and not feature_on('purchase', 'line_contacts')


def test_turned_off_nobody_new_is_named_and_who_is_named_stays(admin, roles, store, holder):
    inv, (line,) = _invoice(store)
    line = _name(admin, inv, line, [{'role': 'warranty_holder', 'contact_id': holder.pk}])
    _switch('invoice', False)
    other = Contact.objects.create(email='lee.other@example.com', name_first='Lee', name_last='Other')
    with pytest.raises(Refused) as refused:
        _name(admin, inv, line, line.refs['contacts'] + [{'role': 'warranty_holder', 'contact_id': other.pk}])
    assert refused.value.code == 'line_contacts_off'
    assert 'Defaults' in str(refused.value)
    line = _name(admin, inv, line, line.refs['contacts'])            # an echo of who is named saves
    assert [r['contact_id'] for r in line.refs['contacts']] == [holder.pk]
    line = _name(admin, inv, line, [])                                # and they can be taken off
    assert _links(holder, 'invoice_line') == []


def test_convert_carries_nobody_to_a_document_whose_switch_is_off(roles, store, holder):
    quote = Quote.objects.create(status='active', customer_id=store.id)
    QuoteLine.objects.create(quote=quote, item={'description': 'Sofa warranty'},
                             price={'unit': 100.0, 'precision': 2}, cost={'unit': 60.0},
                             quantity={'active': 1, 'precision': 2},
                             refs={'contacts': [{'role': 'warranty_holder', 'contact_id': holder.pk}]})
    _switch('order', False)
    order = Order.objects.get(pk=convert_quote_to_order(quote.pk)['order_id'])
    assert not (OrderLine.objects.get(order=order).refs or {}).get('contacts')


def test_the_switch_is_a_default_the_definition_checks(model_defaults):
    from apps.core.services.defaults import checked_defaults
    assert checked_defaults('invoice', {'features': {'line_contacts': True}})['features'] == {'line_contacts': True}
    with pytest.raises(ValueError, match='no switch'):
        checked_defaults('invoice', {'features': {'line_people': True}})
    with pytest.raises(ValueError, match='no switch'):
        checked_defaults('purchase', {'features': {'line_contacts': True}})
    with pytest.raises(ValueError, match='true or false'):
        checked_defaults('invoice', {'features': {'line_contacts': 'yes'}})
