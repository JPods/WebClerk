"""A write must land inside the writer's scope (Bill, 2026-09-23).

The read gates filter rows that exist. A create has no row yet, and an update was checked
only as the row was before the change. So the save door checks the written row against the
actor's role and scope, inside the transaction, and refuses the whole edit if it misses.

Rep scope (Bill, 2026-09-23): a rep reaches the customers whose rep_id is theirs, and a
transaction only when BOTH its own rep_id and its customer's rep_id are theirs. A rep's
new transaction is stamped with the rep's own rep_id by the server.
"""
import pytest

from apps.core.models import Contact
from apps.core.services import access
from apps.core.services.door import Actor, Refused
from apps.core.services.save import save_record
from apps.orgs.models import OrgBase
from apps.transactions.models import Order

pytestmark = pytest.mark.django_db

ORDER_FIELDS = ['id', 'status', 'rep_id', 'customer_id']


def _grant_rep_on_orders():
    from apps.core.models.setting import Setting
    from apps.core.management.commands.seed_rep_access import REP_SCOPE
    setting = Setting.objects.filter(purpose='wc:model', parent_model='order').first()
    config = dict(setting.config or {})
    acc = dict(config.get('access') or {})
    acc['roles'] = {**(acc.get('roles') or {}),
                    'rep': {'view': ORDER_FIELDS, 'edit': ORDER_FIELDS, 'create': True,
                            'scope': REP_SCOPE['order']}}
    config['access'] = acc
    setting.config = config
    setting._setting_update_authorized = True
    setting.save(update_fields=['config'])
    access.clear_cache()


@pytest.fixture
def world():
    _grant_rep_on_orders()
    jane_org = OrgBase.objects.create(company='Jane Sales', org_type='rep')
    other_org = OrgBase.objects.create(company='Other Sales', org_type='rep')
    hers = OrgBase.objects.create(company='Acme', org_type='customer', rep_id=jane_org.pk)
    theirs = OrgBase.objects.create(company='Globex', org_type='customer', rep_id=other_org.pk)
    jane = Contact.objects.create(email='jane.rep@example.com', role='rep', rep_id=jane_org.pk)
    return {'jane': Actor(user=jane), 'mine': jane_org, 'other': other_org,
            'her_customer': hers, 'their_customer': theirs}


def test_a_reps_order_is_stamped_with_their_own_rep(world):
    """Case 1: the rep takes an order for their customer; the server sets the rep."""
    result = save_record(world['jane'], {'model_name': 'order',
                                         'customer_id': world['her_customer'].pk})
    assert Order.objects.get(pk=result.obj_id).rep_id == world['mine'].pk


def test_a_rep_cannot_choose_someone_elses_rep(world):
    """The stamp is the server's: a rep_id the caller sends for a new order is replaced."""
    result = save_record(world['jane'], {'model_name': 'order',
                                         'customer_id': world['her_customer'].pk,
                                         'rep_id': world['other'].pk})
    assert Order.objects.get(pk=result.obj_id).rep_id == world['mine'].pk


def test_a_rep_cannot_take_an_order_for_another_reps_customer(world):
    before = Order.objects.count()
    with pytest.raises(Refused) as refused:
        save_record(world['jane'], {'model_name': 'order',
                                    'customer_id': world['their_customer'].pk})
    assert refused.value.status == 403 and refused.value.code == 'outside_scope'
    assert Order.objects.count() == before, 'the refused create is rolled back'


def test_a_rep_cannot_move_their_order_out_of_reach(world):
    order = save_record(world['jane'], {'model_name': 'order',
                                        'customer_id': world['her_customer'].pk}).obj
    with pytest.raises(Refused) as refused:
        save_record(world['jane'], {'model_name': 'order', 'id': order.pk,
                                    'customer_id': world['their_customer'].pk})
    assert refused.value.code == 'outside_scope'
    order.refresh_from_db()
    assert order.customer_id == world['her_customer'].pk, 'the refused move is rolled back'


def test_our_own_code_is_not_scope_checked(world):
    result = save_record(Actor.system(), {'model_name': 'order',
                                          'customer_id': world['their_customer'].pk,
                                          'rep_id': world['mine'].pk})
    assert Order.objects.filter(pk=result.obj_id).exists()


def test_is_staff_sets_level_four_and_the_higher_wins():
    """One level per contact, the higher (Bill, 2026-09-23)."""
    staff_customer = Contact.objects.create(email='sc@example.com', role='customer', is_staff=True)
    admin = Contact.objects.create(email='sa@example.com', role='admin', is_staff=True)
    flagged_only = Contact.objects.create(email='so@example.com', is_staff=True)
    assert access.level_ceiling(Actor(user=staff_customer)) == 4
    assert access.level_ceiling(Actor(user=admin)) == 9
    assert access.level_ceiling(Actor(user=flagged_only)) == 4
    assert access.is_admin(Actor(user=flagged_only)) is False      # is_staff is not admin


# ── a rep does not see another rep's customer, by any route ─────────────

def _grant_rep(model_key, fields):
    from apps.core.models.setting import Setting
    from apps.core.management.commands.seed_rep_access import REP_SCOPE
    setting = Setting.objects.filter(purpose='wc:model', parent_model=model_key).first()
    config = dict(setting.config or {})
    acc = dict(config.get('access') or {})
    acc['roles'] = {**(acc.get('roles') or {}),
                    'rep': {'view': fields, 'edit': [], 'create': False,
                            'scope': REP_SCOPE[model_key]}}
    config['access'] = acc
    setting.config = config
    setting._setting_update_authorized = True
    setting.save(update_fields=['config'])
    access.clear_cache()


def test_a_rep_sees_only_customers_with_their_rep_id(world):
    from apps.core.services.record_serialize import visible_queryset
    _grant_rep('customer', ['id', 'company', 'rep_id'])
    for org in (world['her_customer'], world['their_customer']):
        OrgBase.objects.filter(pk=org.pk).update(security_level=1)
    seen = set(visible_queryset('customer', actor=world['jane'])[1].values_list('pk', flat=True))
    assert world['her_customer'].pk in seen
    assert world['their_customer'].pk not in seen


def test_a_rep_sees_only_the_contacts_of_their_customers(world):
    """Contacts follow their customer's rep_id — not links, not the contact's own rep."""
    from apps.core.services.record_serialize import visible_queryset
    _grant_rep('contact', ['id', 'email', 'customer_id'])
    hers = Contact.objects.create(email='buyer@acme.example', customer_id=world['her_customer'].pk,
                                  security_level=1)
    theirs = Contact.objects.create(email='buyer@globex.example',
                                    customer_id=world['their_customer'].pk, security_level=1)
    seen = set(visible_queryset('contact', actor=world['jane'])[1].values_list('pk', flat=True))
    assert hers.pk in seen
    assert theirs.pk not in seen


# ── the rep travels with the sale ───────────────────────────────────────

def test_the_rep_travels_quote_to_order_to_invoice(world):
    """Bill, 2026-09-23: the invoice carries the rep, copied from the order. Before, the
    conversion copied neither rep_id nor attention_rep, so a converted order lost its rep
    and fell out of that rep's reach."""
    from apps.transactions.models import Invoice, Quote, QuoteLine
    from apps.transactions.services.convert import convert_order_to_invoice as order_to_invoice
    from apps.transactions.services.convert import convert_quote_to_order as quote_to_order

    quote = Quote.objects.create(customer_id=world['her_customer'].pk, rep_id=world['mine'].pk,
                                 attention_rep='Jane', terms='Net 30',
                                 finance={'tax': {'rate': 7.5}})
    QuoteLine.objects.create(quote=quote, status='OPEN', item={"id_num": 1},
                             quantity={"active": 1}, price={"amount": 1})
    made = quote_to_order.transfer_quote_to_order(quote=quote, transfer_all=True)
    order = Order.objects.get(pk=(made.get('data') or made)['order_id'])
    assert (order.rep_id, order.attention_rep) == (world['mine'].pk, 'Jane')

    from apps.transactions.models import OrderLine
    if not OrderLine.objects.filter(order=order).exists():
        OrderLine.objects.create(order=order, status='OPEN', item={"id_num": 1},
                                 quantity={"active": 1}, price={"amount": 1})
    made = order_to_invoice.transfer_order_to_invoice(order=order, transfer_all=True)
    invoice = Invoice.objects.get(pk=(made.get('data') or made)['invoice_id'])
    assert (invoice.rep_id, invoice.attention_rep) == (world['mine'].pk, 'Jane')
    # The one engine carries the sale's terms and tax setup; the old invoice builder did not.
    assert invoice.terms == 'Net 30'
    assert (invoice.finance or {}).get('tax', {}).get('rate') == 7.5
