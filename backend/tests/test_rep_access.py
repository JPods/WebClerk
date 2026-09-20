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
    rep_org = OrgBase.objects.create(display_name='Rep Co', org_type='rep')
    user = _login(django_user_model, 'rep@example.fake', 'rep', rep=rep_org)

    context = build_user_context(user)

    assert context['org_ids']['rep'] == [rep_org.pk]
    assert context['roles'] == ['rep']


@pytest.mark.django_db
def test_the_scope_resolves_and_narrows_to_assigned_rows(django_user_model):
    """The filters are real ORM paths, and they exclude what is not assigned."""
    from apps.transactions.models import Order

    rep_org = OrgBase.objects.create(display_name='Rep Co', org_type='rep')
    other_rep = OrgBase.objects.create(display_name='Other Rep', org_type='rep')
    mine = OrgBase.objects.create(display_name='My Customer', org_type='customer')
    theirs = OrgBase.objects.create(display_name='Their Customer', org_type='customer')

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
    setting = Setting.objects.filter(purpose='wc:model', parent_model='order',
                                     is_deleted=False).first()
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
