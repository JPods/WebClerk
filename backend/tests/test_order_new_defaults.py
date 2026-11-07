"""Defaults: one home, one moment, the org first (readme 106; Bill, 2026-11-05/06/07).

Every record is born with its model's company defaults — the save that first gives it an ida
fills its blanks (core/services/defaults.py, called by the save door): a document's terms,
price_level retail, dt_needed = born + days, priority; a customer's terms and level; a vendor's
terms. A document takes its party's values when its customer or vendor is set (party_fill).
The server computes them; the form shows what the save returns."""
import time

import pytest

from apps.core.models import Setting
from apps.core.services.door import Actor, Refused
from apps.core.services.new import new_record
from apps.core.services.save import save_record
from apps.core.models import Contact
from apps.orgs.models import Customer, Vendor
from apps.transactions.models import Order, Purchase, Quote, Receipt

pytestmark = pytest.mark.django_db

DAY_MS = 86_400_000


@pytest.fixture
def admin(django_user_model):
    return django_user_model.objects.create_superuser(
        email='orders@example.com', password=None, name_first='Or', name_last='Der', username='')


@pytest.fixture
def company(model_defaults):
    """Each model's definition carries the shipped defaults (readme 106 A); N10 is a Term too."""
    from apps.accounts.models import Term
    Term.objects.get_or_create(ida='N10', defaults={'name': 'N10', 'is_active': True})
    return Setting.objects.get(purpose='wc:company_profile')


def _as(user):
    return Actor(user=user, kind='user', source='wcapi')


def _born(admin, **payload):
    return Order.objects.get(pk=new_record(_as(admin), 'order', dict(payload)).obj_id)


def test_an_order_is_born_with_the_company_defaults(admin, company):
    before = int(time.time() * 1000)
    order = _born(admin)
    assert order.priority == 'medium'
    assert order.price_level == 'retail'
    assert before + 14 * DAY_MS <= order.dt_needed <= before + 14 * DAY_MS + 60_000
    assert order.terms == 'N30'   # the company's until a customer says otherwise


@pytest.mark.parametrize('model_key,Model', [('quote', Quote), ('purchase', Purchase), ('receipt', Receipt)])
def test_every_document_is_born_with_the_company_defaults(admin, company, model_key, Model):
    """Bill walked the simulator on 2026-11-06: a quote and a purchase were born bare."""
    before = int(time.time() * 1000)
    doc = Model.objects.get(pk=new_record(_as(admin), model_key, {}).obj_id)
    assert (doc.priority, doc.price_level, doc.terms) == ('medium', 'retail', 'N30')
    assert before + 14 * DAY_MS <= doc.dt_needed <= before + 14 * DAY_MS + 60_000


def test_a_vendor_gives_its_terms_to_a_purchase(admin, company):
    seller = Vendor.objects.create(company='Terms Seller', terms='N10')
    po = Purchase.objects.get(pk=new_record(_as(admin), 'purchase', {}).obj_id)
    save_record(_as(admin), {'id': po.pk, 'version': po.version, 'vendor_id': seller.pk}, model_key='purchase')
    po.refresh_from_db()
    assert po.terms == 'N10'


def test_a_customer_with_terms_and_a_level_gives_them_to_the_order(admin, company):
    buyer = Customer.objects.create(company='Terms Buyer', terms='N10', price_level='wholesale')
    order = _born(admin)
    save_record(_as(admin), {'id': order.pk, 'version': order.version, 'customer_id': buyer.pk}, model_key='order')
    order.refresh_from_db()
    assert (order.terms, order.price_level) == ('N10', 'wholesale')


def test_a_customer_without_them_leaves_the_company_terms_and_retail(admin, company):
    buyer = Customer.objects.create(company='Plain Buyer')
    order = _born(admin)
    save_record(_as(admin), {'id': order.pk, 'version': order.version, 'customer_id': buyer.pk}, model_key='order')
    order.refresh_from_db()
    assert (order.terms, order.price_level) == ('N30', 'retail')


def test_what_the_person_types_in_the_same_save_is_theirs(admin, company):
    buyer = Customer.objects.create(company='Terms Buyer', terms='N10', price_level='wholesale')
    order = _born(admin)
    save_record(_as(admin), {'id': order.pk, 'version': order.version, 'customer_id': buyer.pk,
                             'terms': 'N30', 'price_level': 'retail', 'priority': 'high'}, model_key='order')
    order.refresh_from_db()
    assert (order.terms, order.price_level, order.priority) == ('N30', 'retail', 'high')


def test_a_later_save_does_not_rewrite_the_defaults(admin, company):
    buyer = Customer.objects.create(company='Terms Buyer', terms='N10')
    order = _born(admin)
    save_record(_as(admin), {'id': order.pk, 'version': order.version, 'customer_id': buyer.pk}, model_key='order')
    order.refresh_from_db()
    save_record(_as(admin), {'id': order.pk, 'version': order.version, 'terms': 'N30', 'priority': 'low'}, model_key='order')
    order.refresh_from_db()
    save_record(_as(admin), {'id': order.pk, 'version': order.version, 'comments': {'public': 'unrelated'}}, model_key='order')
    order.refresh_from_db()
    assert (order.terms, order.priority) == ('N30', 'low')


def test_a_default_terms_that_is_no_term_is_refused_where_it_is_set(admin, company, model_defaults):
    """The gate is the definition's save (checked_defaults): a wrong term never reaches a birth."""
    from django.core.exceptions import ValidationError
    setting = model_defaults['order']
    setting.config = {**setting.config, 'defaults': {'fields': {'terms': 'net45'}}}
    setting._setting_create_authorized = True
    with pytest.raises(ValidationError, match='default terms'):
        setting.save()


def test_a_definition_written_behind_the_gate_still_bites_at_birth(admin, company, model_defaults):
    """A queryset update skips Setting.save: the newborn is refused with the valid idas, never
    born with a term that does not exist (fail fast, never silent)."""
    from apps.core.services import definition
    Setting.objects.filter(pk=model_defaults['order'].pk).update(
        config={**model_defaults['order'].config, 'defaults': {'fields': {'terms': 'net45'}, 'formatting': {}}})
    definition.clear()
    with pytest.raises(Refused) as refused:
        _born(admin)
    assert refused.value.code == 'invalid_terms' and 'defaults.fields.terms' in refused.value.message


@pytest.mark.parametrize('model_key,Model,expected', [
    ('customer', Customer, {'terms': 'N30', 'price_level': 'retail'}),
    ('vendor', Vendor, {'terms': 'N30', 'price_level': None}),
])
def test_an_org_is_born_with_the_company_defaults(admin, company, model_key, Model, expected):
    """Bill, 2026-11-07: Rubble Manufacturing passed nothing on because it had no terms and no
    level — new orgs were never born with the company's."""
    org = Model.objects.get(pk=new_record(_as(admin), model_key, {}).obj_id)
    assert {k: getattr(org, k) for k in expected} == expected
    assert org.ida, 'the moment is the ida'


def test_a_record_that_already_has_an_ida_is_not_filled(admin, company):
    """The moment is the first ida, once: a record made outside the door has one, so a later
    save through the door leaves its blanks alone (the sweep repairs existing records)."""
    buyer = Customer.objects.create(company='Old Buyer')
    assert buyer.ida and buyer.terms is None
    save_record(_as(admin), {'id': buyer.pk, 'version': buyer.version, 'comments': {'public': 'hello'}}, model_key='customer')
    buyer.refresh_from_db()
    assert buyer.terms is None and buyer.price_level is None


def test_a_blank_the_person_leaves_is_not_refilled(admin, company):
    """No fill on every save: a cleared priority stays cleared (106 rule 4)."""
    order = _born(admin)
    save_record(_as(admin), {'id': order.pk, 'version': order.version, 'priority': ''}, model_key='order')
    order.refresh_from_db()
    save_record(_as(admin), {'id': order.pk, 'version': order.version, 'comments': {'public': 'later'}}, model_key='order')
    order.refresh_from_db()
    assert not order.priority


def test_a_model_without_a_block_is_born_as_it_is(admin, company):
    """A contact has no defaults block yet (106 open B: source_name): nothing is written."""
    contact = Contact.objects.get(pk=new_record(_as(admin), 'contact', {}).obj_id)
    assert contact.ida and not contact.source_name


def test_a_record_whose_payload_names_it_is_filled_like_a_newborn(admin, company):
    """An import or a bundle carries the ida in the create: that save is still the one that
    first names the record, so its blanks are filled (the lead's review of 2038bf4)."""
    saved = save_record(_as(admin), {'model_name': 'customer', 'ida': 'IMP-1', 'company': 'Imported Co'}, model_key='customer')
    imported = Customer.objects.get(pk=saved.obj_id)
    assert (imported.ida, imported.terms, imported.price_level) == ('IMP-1', 'N30', 'retail')
