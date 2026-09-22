"""A rep is staff, with a salesperson's fields on their own customers and documents.

Bill, 2026-09-20: *"Reps need to behave like staff"*, then *"Reps match sales but only for
customers and order to which their rep_id is assigned."*

Fields by enumeration, rows by scope — the access model as designed. Seeded here because
wc_demo has no rep login and no customer contact carrying a rep_id, so nothing exercises
this rule against real data yet.
"""
import pytest
from django.utils.crypto import get_random_string

from apps.core.services import access
from apps.orgs.models import OrgBase


def _login(django_user_model, email, role, **kwargs):
    return django_user_model.objects.create_user(
        email=email, password=get_random_string(20), role=role,
        name_first='P', name_last='User', **kwargs)


def test_a_rep_is_staff_not_a_person_outside_the_company():
    assert 'rep' in access.STAFF_ROLES
    assert 'rep' not in access.PORTAL_ROLES
    # and so is not swept into the portal order rewrite, which looks up a customer org a
    # rep does not have — the reason a rep could not raise an order at all
    assert access.PORTAL_ORDER_ROLES == ('customer', 'buyer')


@pytest.mark.django_db
def test_the_rep_org_reaches_the_user_context(django_user_model):
    """Without this token there is nothing for a rep's scope to be written against."""
    from apps.core.services.role_filter import build_user_context
    rep_org = OrgBase.objects.create(company='Rep Co', org_type='rep')
    user = _login(django_user_model, 'rep@example.fake', 'rep', rep=rep_org)

    context = build_user_context(user)

    assert context['org_ids']['rep'] == [rep_org.pk]
    assert context['roles'] == ['rep']


@pytest.mark.django_db
def test_the_scope_resolves_and_narrows_to_assigned_rows(django_user_model):
    """The filters are real ORM paths, and they exclude what is not assigned."""
    from apps.transactions.models import Order

    rep_org = OrgBase.objects.create(company='Rep Co', org_type='rep')
    other_rep = OrgBase.objects.create(company='Other Rep', org_type='rep')
    mine = OrgBase.objects.create(company='My Customer', org_type='customer')
    theirs = OrgBase.objects.create(company='Their Customer', org_type='customer')

    my_contact = _login(django_user_model, 'mine@example.fake', 'customer',
                        customer=mine, rep=rep_org)
    their_contact = _login(django_user_model, 'theirs@example.fake', 'customer',
                           customer=theirs, rep=other_rep)

    my_order = Order.objects.create(customer_id=mine.pk, contact_id=my_contact.pk)
    Order.objects.create(customer_id=theirs.pk, contact_id=their_contact.pk)

    visible = Order.objects.filter(contact__rep_id__in=[rep_org.pk])
    assert list(visible.values_list('pk', flat=True)) == [my_order.pk]

    customers = OrgBase.objects.filter(
        org_type='customer', contacts_as_customer__rep_id__in=[rep_org.pk]).distinct()
    assert list(customers.values_list('pk', flat=True)) == [mine.pk]


@pytest.mark.django_db
def test_a_rep_holds_the_sales_field_lists_not_a_narrower_copy():
    """Copied from sales, so there is no second list to drift. It used to be trimmed by
    the portal rules: 168 edit leaves against sales' 469 on an order."""
    from django.core.management import call_command

    from apps.core.models.setting import Setting
    from apps.core.management.commands.seed_rep_access import REP_SCOPE

    # Update the model's own Setting rather than adding a second one: purpose +
    # parent_model is not unique, and the command reads whichever .first() returns.
    setting = Setting.objects.filter(purpose='wc:model', parent_model='order').first()
    assert setting is not None, "the order model has no wc:model Setting"
    config = dict(setting.config or {})
    acc = dict(config.get('access') or {})
    roles = dict(acc.get('roles') or {})
    roles['sales'] = {'view': ['@all'], 'edit': ['@all'], 'scope': {}, 'create': True}
    roles['rep'] = {'view': ['status'], 'edit': [], 'scope': {}, 'create': True}
    acc['roles'] = roles
    config['access'] = acc
    setting.config = config
    setting._setting_update_authorized = True
    setting.save(update_fields=['config'])
    access.clear_cache()

    call_command('seed_rep_access', '--apply')

    block = access.model_access('order')['rep']
    sales = access.model_access('order')['sales']
    assert block['edit'] == sales['edit']          # the same list, not a narrower copy
    assert block['view'] == sales['view']
    assert block['scope'] == REP_SCOPE['order']    # but only their own rows
    assert block['edit_scope'] == REP_SCOPE['order']
    assert block['delete'] is False                # a rep does not delete company records
    access.clear_cache()


@pytest.mark.django_db
def test_a_rep_can_price_what_they_quote_and_writes_nothing_to_items():
    """Bill, 2026-09-20: "they can access items in proposals and orders. If they cannot do
    that without accessing the item model, then we give them access to items as well",
    "They cannot write to items", and "sales does not need to edit items either".

    A rep held id/ida/name/sku/description — enough to name an item, not to price it; a
    customer could see more of an item than a rep could. The read side now matches sales.
    The write side is refused in REP_READ_ONLY rather than inherited, so a later grant to
    sales could not quietly hand a rep the catalogue.
    """
    from django.core.management import call_command

    from apps.core.models.setting import Setting
    from apps.core.management.commands.seed_rep_access import REP_READ_ONLY

    assert 'item' in REP_READ_ONLY
    setting = Setting.objects.filter(purpose='wc:model', parent_model='item').first()
    assert setting is not None
    config = dict(setting.config or {})
    acc = dict(config.get('access') or {})
    roles = dict(acc.get('roles') or {})
    roles['sales'] = {'view': ['id', 'name', 'price.base', 'quantity.on_hand'],
                      'edit': [], 'scope': {}, 'create': False, 'delete': False}
    roles['rep'] = {'view': ['id', 'name'], 'edit': [], 'scope': {}, 'create': False}
    acc['roles'] = roles
    config['access'] = acc
    setting.config = config
    setting._setting_update_authorized = True
    setting.save(update_fields=['config'])
    access.clear_cache()

    call_command('seed_rep_access', '--apply')

    rep = access.model_access('item')['rep']
    assert 'price.base' in rep['view']          # can price what they quote
    assert 'quantity.on_hand' in rep['view']    # and see whether there is any
    assert rep['edit'] == []                    # and writes nothing
    assert rep['create'] is False and rep['delete'] is False
    access.clear_cache()


@pytest.mark.django_db
def test_selling_roles_do_not_write_the_catalogue():
    """Who may change an item: not sales, not rep (Bill, 2026-09-20)."""
    acc = access.model_access('item')
    for role in ('sales', 'rep'):
        block = acc.get(role) or {}
        assert not block.get('edit'), f"{role} should not edit items"
        assert not block.get('create'), f"{role} should not create items"
        assert not block.get('delete'), f"{role} should not delete items"
