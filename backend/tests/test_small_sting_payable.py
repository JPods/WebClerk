"""A Small-Sting creates a payable (Bill, 2026-10-22).

- $1.72 unless the sting names its value; a P&L event.
- Owed to the person who filed it, never their org.
- Dr 6550-small_sting_expense / Cr 2230-small_stings_payable.
- Paid in cash like any payable (Dr 2230 / Cr cash); it ages in aged payables until then.

Classes, review and due date (Bill's rulings, same day):
- Due Net 10, or the term named at company profile config.small_stings.term.
- The company defines classes (inconvenience $25, safety_breach $100 reviewed in the demo); a
  sting names one, which sets its amount. An unknown class is refused with the classes.
- The payable is created at once, before the review; a reviewed one is not paid until staff
  approve. Reject reverses the journal and closes the payable, deleting nothing.

And the two AP defects fixed on the same branch: aged payables read model_name='purchase'
(payables are 'receipt', so it showed none), and a payment of a receipt debited an expense
instead of accounts payable.
"""
from decimal import Decimal

import pytest

from tests.utils import received_receipt_line

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures('chart_of_accounts')]

STING_EXPENSE = '6550-small_sting_expense'
STING_PAYABLE = '2230-small_stings_payable'


@pytest.fixture(autouse=True)
def n10(db):
    """A sting is due Net 10 unless the company names another term (seed_terms has N10)."""
    from apps.accounts.models import Term
    Term.objects.get_or_create(ida='N10', defaults={'name': 'N10', 'description': 'Net 10 Days',
                                                    'days_due': 10, 'is_active': True})


DEMO_CLASSES = [
    {'key': 'inconvenience', 'label': 'Inconvenience', 'amount': 25.0, 'review': False},
    {'key': 'safety_breach', 'label': 'Valid safety breach', 'amount': 100.0, 'review': True},
]


def _set_stings(**block):
    from apps.core.models import Setting
    company = Setting.objects.get(purpose='wc:company_profile')
    company.config = {**company.config, 'small_stings': block}
    company._setting_update_authorized = True
    company.save()


@pytest.fixture
def classes():
    _set_stings(term='N10', classes=DEMO_CLASSES)


@pytest.fixture
def filer(django_user_model):
    from apps.orgs.models import OrgBase
    org = OrgBase.objects.create(company='Stung Customer Co', org_type='customer', is_active=True)
    return django_user_model.objects.create_user(email='filer@sting.test', password='x', username='',
                                                 role='admin', customer=org)


@pytest.fixture
def filer_client(client, filer):
    client.force_login(filer)
    return client


def _actor(user):
    from apps.core.services.door import Actor
    return Actor(user=user, kind='user', source='command')


def _file(user, **kw):
    from apps.accounts.services.small_sting import file_small_sting
    return file_small_sting(_actor(user), complaint=kw.pop('complaint', 'Pod stalled at Station 4'), **kw)


def _net(source_model, source_id, account):
    from apps.accounts.models import GlJournal
    rows = GlJournal.objects.filter(source_model=source_model, source_id=source_id, account=account)
    return round(sum(Decimal(str(r.debit or 0)) - Decimal(str(r.credit or 0)) for r in rows), 2)


def _payees():
    from apps.accounts.services.aged_payables import aged_payables_report
    return {(v['payee_model'], v['id']): v for v in aged_payables_report()['vendors']}


def test_a_sting_with_no_value_is_a_payable_of_1_72_owed_to_the_filer(filer):
    from apps.accounts.models import Ledger
    from apps.core.models import Action
    from apps.core.models.pending import Pending
    from apps.transactions.models import Receipt, ReceiptLine
    out = _file(filer)
    action = Action.objects.get(pk=out['action_id'])
    assert action.ida.startswith('STING-') and action.metadata['type'] == 'small_sting'
    assert action.contact_id == filer.pk

    receipt = Receipt.objects.get(pk=out['receipt_id'])
    assert receipt.source_type == 'small_sting'
    assert (receipt.contact_id, receipt.vendor_id) == (filer.pk, None), 'the filer, not their org'
    assert (receipt.parent_model, receipt.parent_id) == ('action', action.pk)
    assert Decimal(str(receipt.totals['total'])) == Decimal('1.72')

    line = ReceiptLine.objects.get(receipt=receipt)
    assert line.item_fk_id is None
    assert line.item['description'] == f'{action.ida}: Pod stalled at Station 4'

    ledger = Ledger.objects.get(parent_id=receipt.pk, model_name='receipt')
    assert (ledger.source, ledger.contact_id, ledger.org_id) == ('AP', filer.pk, None)
    assert ledger.value_available == Decimal('1.72')
    assert not Pending.objects.filter(purpose='small_sting').exists(), 'no writer without a reader'


def test_a_sting_that_names_its_value_is_owed_that_value(filer):
    from apps.transactions.models import Receipt
    out = _file(filer, amount='25.00')
    assert out['amount'] == 25.0
    assert Decimal(str(Receipt.objects.get(pk=out['receipt_id']).totals['total'])) == Decimal('25.00')


def test_the_payee_is_the_filing_contact_named(filer):
    from apps.core.models import Contact
    other = Contact.objects.create(email='other@sting.test', name_first='Other')
    out = _file(filer, contact_id=other.pk)
    assert out['payee_contact_id'] == other.pk
    assert ('contact', other.pk) in _payees()


def test_the_sting_posts_balanced_to_its_own_accounts(filer):
    out = _file(filer, amount='3.00')
    assert _net('receipt', out['receipt_id'], STING_EXPENSE) == Decimal('3.00')
    assert _net('receipt', out['receipt_id'], STING_PAYABLE) == Decimal('-3.00')
    assert _net('receipt', out['receipt_id'], '2050-received_not_billed') == 0
    from apps.accounts.models import GlJournal
    rows = GlJournal.objects.filter(source_model='receipt', source_id=out['receipt_id'])
    assert sum(r.debit or 0 for r in rows) == sum(r.credit or 0 for r in rows)


def test_the_sting_ages_in_aged_payables_under_the_filer(filer):
    out = _file(filer)
    section = _payees()[('contact', filer.pk)]
    assert section['balance_due'] == 1.72
    assert [l['parent_id'] for l in section['lines']] == [out['receipt_id']]


def test_paying_the_sting_in_cash_clears_it_and_posts_against_the_sting_payable(filer, filer_client):
    from apps.accounts.models import Ledger
    from apps.accounts.services.journalize import journalize_cash
    from apps.transactions.models import Cash, Receipt
    out = _file(filer)
    r = filer_client.post(f'/wcapi/receipt/{out["receipt_id"]}/add_cash/',
                          {'amount': '1.72', 'method': 'cash'}, content_type='application/json')
    assert r.status_code == 200, r.content
    data = r.json()['data']
    data = data.get('result', data)
    assert data['applied']['state'] == 'applied', data
    cash = Cash.objects.get(pk=data['cash_id'])
    assert (cash.amount, cash.contact_id, cash.vendor_id) == (Decimal('-1.72'), filer.pk, None)
    assert cash.available == Decimal('0.00')

    receipt = Receipt.objects.get(pk=out['receipt_id'])
    assert (float(receipt.totals['paid']), float(receipt.totals['balance'])) == (1.72, 0.0)
    assert Ledger.objects.get(parent_id=receipt.pk, model_name='receipt').value_available == 0
    assert ('contact', filer.pk) not in _payees()

    posted = journalize_cash(cash.pk)
    assert posted['created'] == 2, posted
    assert _net('cash', cash.pk, STING_PAYABLE) == Decimal('1.72')
    assert _net('cash', cash.pk, '1000-cash') == Decimal('-1.72')
    assert _net('cash', cash.pk, '6950-general_admin') == 0, 'never expensed twice'


def test_a_payment_to_someone_else_does_not_pay_the_sting(filer):
    from apps.core.models import Contact
    from apps.transactions.models import Cash
    from apps.transactions.services.cash.cash_pending_receipt import apply_cash_to_receipt
    out = _file(filer)
    stranger = Contact.objects.create(email='stranger@sting.test')
    cash = Cash.objects.create(contact_id=stranger.pk, amount=Decimal('-1.72'), status='completed')
    with pytest.raises(ValueError, match='owed to contact'):
        apply_cash_to_receipt(cash.pk, out['receipt_id'], Decimal('1.72'))


@pytest.mark.parametrize('amount', ['-1', '0', 'lots'])
def test_a_bad_amount_is_refused_and_nothing_is_filed(filer, amount):
    from apps.core.models import Action
    from apps.core.services.door import Refused
    from apps.transactions.models import Receipt
    with pytest.raises(Refused) as refused:
        _file(filer, amount=amount)
    assert refused.value.code == 'sting_amount'
    assert not Action.objects.exists() and not Receipt.objects.exists()


def test_a_sting_that_cannot_post_leaves_nothing_half_made(filer):
    from apps.accounts.models import Ledger
    from apps.core.models import Action, Setting
    from apps.core.services.door import Refused
    from apps.transactions.models import Receipt
    company = Setting.objects.get(purpose='wc:company_profile')
    gl = dict(company.config['gl_defaults'])
    gl.pop('small_sting_expense')
    company.config = {**company.config, 'gl_defaults': gl}
    company._setting_update_authorized = True
    company.save()
    with pytest.raises(Refused) as refused:
        _file(filer)
    assert refused.value.code == 'sting_journal'
    assert 'small_sting_expense' in refused.value.message, 'names the role to map'
    assert not Action.objects.exists() and not Receipt.objects.exists() and not Ledger.objects.exists()


def test_filing_through_manage_is_refused_without_a_signed_in_person(client):
    r = client.post('/wcapi/_manage/', {'action': 'file_small_sting',
                                        'params': {'complaint': 'x'}}, content_type='application/json')
    assert r.status_code in (401, 403), r.content


def test_filing_through_manage_creates_the_payable(filer_client, filer):
    r = filer_client.post('/wcapi/_manage/', {'action': 'file_small_sting',
                                              'params': {'complaint': 'Door jammed', 'severity': 2}},
                          content_type='application/json')
    assert r.status_code == 200, r.content
    assert r.json()['data']['amount'] == 1.72
    assert ('contact', filer.pk) in _payees()


def test_period_close_ages_payables_owed_to_a_contact(filer):
    from datetime import date
    from apps.accounts.services.period_close import _compute_aging_for_source
    _file(filer)
    contacts = {}
    _compute_aging_for_source('AP', date.today(), contact_aging=contacts)
    assert contacts[str(filer.pk)]['total'] == 1.72


def test_an_installed_chart_gets_the_sting_accounts_and_roles_from_the_migration():
    import importlib
    from django.apps import apps
    from apps.accounts.models import GlAccount
    from apps.core.models import Setting
    migration = importlib.import_module('apps.accounts.migrations.0019_ledger_contact_small_sting_accounts')
    GlAccount.objects.filter(ida__in=(STING_EXPENSE, STING_PAYABLE)).delete()
    company = Setting.objects.get(purpose='wc:company_profile')
    gl = {k: v for k, v in company.config['gl_defaults'].items()
          if k not in ('small_sting_expense', 'small_stings_payable')}
    gl['accounts_payable'] = '2000-accounts_payable'
    Setting.objects.filter(pk=company.pk).update(config={**company.config, 'gl_defaults': gl})

    migration.add_sting_accounts_and_roles(apps, None)

    assert GlAccount.objects.filter(ida__in=(STING_EXPENSE, STING_PAYABLE), is_active=True).count() == 2
    gl = Setting.objects.get(pk=company.pk).config['gl_defaults']
    assert (gl['small_sting_expense'], gl['small_stings_payable']) == (STING_EXPENSE, STING_PAYABLE)


# ── The two AP defects ────────────────────────────────────────────────

def _vendor_receipt(unit=100.0):
    from apps.orgs.models import OrgBase
    from apps.transactions.models import Receipt
    vendor = OrgBase.objects.create(company='AP Vendor', org_type='vendor', is_active=True)
    receipt = Receipt.objects.create(vendor_id=vendor.pk)
    received_receipt_line(receipt=receipt, quantity={'active': 1}, cost={'unit': unit, 'precision': 2})
    receipt.refresh_from_db()
    return vendor, receipt


def test_aged_payables_shows_a_vendor_receipt_payable():
    vendor, receipt = _vendor_receipt(100.0)
    section = _payees()[('org', vendor.pk)]
    assert section['balance_due'] == 100.0 and section['lines'][0]['type'] == 'RC'


def test_paying_a_vendor_receipt_debits_accounts_payable_not_an_expense(filer_client):
    from apps.accounts.services.journalize import journalize_cash
    from apps.transactions.models import Cash
    vendor, receipt = _vendor_receipt(100.0)
    r = filer_client.post(f'/wcapi/receipt/{receipt.pk}/add_cash/', {'amount': '60.00', 'method': 'check'},
                          content_type='application/json')
    assert r.status_code == 200, r.content
    data = r.json()['data']
    cash = Cash.objects.get(pk=data.get('result', data)['cash_id'])
    assert journalize_cash(cash.pk)['created'] == 2
    assert _net('cash', cash.pk, '2000-accounts_payable') == Decimal('60.00')
    assert _net('cash', cash.pk, '1000-cash') == Decimal('-60.00')
    assert _net('cash', cash.pk, '6950-general_admin') == 0


def test_a_payment_that_pays_no_payable_is_still_a_direct_expense():
    from apps.accounts.services.journalize import journalize_cash
    from apps.transactions.models import Cash
    cash = Cash.objects.create(amount=Decimal('-12.00'), status='completed', category='')
    journalize_cash(cash.pk)
    assert _net('cash', cash.pk, '6950-general_admin') == Decimal('12.00')


def test_a_customer_files_a_sting_only_for_themself(filer, django_user_model):
    from apps.core.services.door import Refused
    from apps.orgs.models import OrgBase
    org = OrgBase.objects.create(company='Portal Co', org_type='customer', is_active=True)
    customer = django_user_model.objects.create_user(email='portal@sting.test', password='x',
                                                     username='', role='customer', customer=org)
    with pytest.raises(Refused) as e:
        _file(customer, contact_id=filer.pk)
    assert e.value.code == 'sting_payee'
    assert _file(customer)['payee_contact_id'] == customer.pk
    # Staff may file one phoned in by someone else.
    assert _file(filer, contact_id=customer.pk)['payee_contact_id'] == customer.pk


# ── Due date, classes and review (Bill, 2026-10-22) ───────────────────


def test_a_sting_is_due_net_10_by_default(filer):
    from datetime import timedelta
    from django.utils import timezone
    from apps.accounts.models import Ledger
    from apps.transactions.models import Receipt
    out = _file(filer)
    receipt = Receipt.objects.get(pk=out['receipt_id'])
    assert (out['term'], receipt.terms) == ('N10', 'N10')
    ledger = Ledger.objects.get(parent_id=receipt.pk, model_name='receipt')
    assert abs(ledger.dt_due - (timezone.now() + timedelta(days=10))) < timedelta(minutes=5)


def test_the_company_profile_names_the_sting_term(filer):
    from datetime import timedelta
    from django.utils import timezone
    from apps.accounts.models import Ledger
    _set_stings(term='n30')                      # stored in the Term's own spelling
    out = _file(filer)
    assert out['term'] == 'N30'
    ledger = Ledger.objects.get(parent_id=out['receipt_id'], model_name='receipt')
    assert abs(ledger.dt_due - (timezone.now() + timedelta(days=30))) < timedelta(minutes=5)


def test_a_sting_term_that_is_not_a_term_is_refused_before_anything_is_written(filer):
    from apps.core.models import Action
    from apps.core.services.door import Refused
    _set_stings(term='N7')
    with pytest.raises(Refused) as e:
        _file(filer)
    assert e.value.code == 'sting_term' and 'N10' in e.value.message and 'N30' in e.value.message
    assert not Action.objects.exists()


@pytest.mark.parametrize('key,amount,review', [('inconvenience', '25.00', 'not_required'),
                                               ('safety_breach', '100.00', 'pending')])
def test_a_class_sets_the_amount_and_the_review(filer, classes, key, amount, review):
    from apps.core.models import Action
    from apps.transactions.models import Receipt
    out = _file(filer, sting_class_key=key)
    assert (out['class'], out['amount'], out['review']) == (key, float(amount), review)
    assert Decimal(str(Receipt.objects.get(pk=out['receipt_id']).totals['total'])) == Decimal(amount)
    meta = Action.objects.get(pk=out['action_id']).metadata
    assert (meta['class'], meta['review']['state']) == (key, review)
    # The payable and its journal are written at filing, review or not.
    assert _net('receipt', out['receipt_id'], STING_PAYABLE) == -Decimal(amount)


def test_a_class_amount_is_not_overridden(filer, classes):
    from apps.core.services.door import Refused
    from apps.transactions.models import Receipt
    assert _file(filer, sting_class_key='Inconvenience', amount='25')['amount'] == 25.0
    with pytest.raises(Refused) as e:
        _file(filer, sting_class_key='inconvenience', amount='500')
    assert e.value.code == 'sting_amount' and '$25.00' in e.value.message
    assert Receipt.objects.count() == 1


def test_an_unknown_class_is_refused_with_the_classes(filer, classes):
    from apps.core.models import Action
    from apps.core.services.door import Refused
    with pytest.raises(Refused) as e:
        _file(filer, sting_class_key='rudeness')
    assert e.value.code == 'sting_class'
    assert 'inconvenience' in e.value.message and 'safety_breach' in e.value.message
    assert not Action.objects.exists()


def test_a_class_with_no_classes_defined_is_refused(filer):
    from apps.core.services.door import Refused
    with pytest.raises(Refused) as e:
        _file(filer, sting_class_key='inconvenience')
    assert e.value.code == 'sting_class' and 'defines no sting classes' in e.value.message


def test_a_sting_under_review_is_not_paid(filer, filer_client, classes):
    from apps.transactions.models import Cash
    from apps.transactions.services.cash.cash_pending_receipt import apply_cash_to_receipt
    out = _file(filer, sting_class_key='safety_breach')
    r = filer_client.post(f'/wcapi/receipt/{out["receipt_id"]}/add_cash/',
                          {'amount': '100.00', 'method': 'cash'}, content_type='application/json')
    assert r.status_code == 409, r.content
    assert 'under review' in r.json()['message']
    assert not Cash.objects.exists(), 'refused before any cash is saved'
    cash = Cash.objects.create(contact_id=filer.pk, amount=Decimal('-100.00'), status='completed')
    with pytest.raises(ValueError, match='under review'):
        apply_cash_to_receipt(cash.pk, out['receipt_id'], Decimal('100.00'))


def test_approve_then_pay(filer, filer_client, classes):
    from apps.core.models import Action
    from apps.transactions.models import Receipt
    out = _file(filer, sting_class_key='safety_breach')
    r = filer_client.post('/wcapi/_manage/', {'action': 'approve_small_sting',
                                              'params': {'receipt_id': out['receipt_id'], 'note': 'CCTV confirms'}},
                          content_type='application/json')
    assert r.status_code == 200, r.content
    review = Action.objects.get(pk=out['action_id']).metadata['review']
    assert (review['state'], review['reviewed_by'], review['note']) == ('approved', filer.pk, 'CCTV confirms')
    assert review['dt_reviewed'] > 1_700_000_000_000, 'UTC epoch ms'
    r = filer_client.post(f'/wcapi/receipt/{out["receipt_id"]}/add_cash/',
                          {'amount': '100.00', 'method': 'cash'}, content_type='application/json')
    assert r.status_code == 200, r.content
    assert float(Receipt.objects.get(pk=out['receipt_id']).totals['balance']) == 0.0
    from apps.core.services.door import Refused
    from apps.accounts.services.small_sting import approve_small_sting
    with pytest.raises(Refused) as e:
        approve_small_sting(_actor(filer), action_id=out['action_id'])
    assert e.value.code == 'sting_not_under_review'


def test_reject_reverses_the_journal_and_closes_the_payable(filer, filer_client, classes):
    from apps.accounts.models import GlJournal, Ledger
    from apps.core.models import Action
    from apps.transactions.models import Receipt
    out = _file(filer, sting_class_key='safety_breach')
    r = filer_client.post('/wcapi/_manage/', {'action': 'reject_small_sting',
                                              'params': {'action_id': out['action_id']}},
                          content_type='application/json')
    assert r.status_code == 400 and 'reason' in r.json()['message'], 'a reason is required'
    r = filer_client.post('/wcapi/_manage/', {'action': 'reject_small_sting',
                                              'params': {'action_id': out['action_id'],
                                                         'reason': 'No breach on the footage'}},
                          content_type='application/json')
    assert r.status_code == 200, r.content
    assert r.json()['data']['reversed_rows'] == 2

    # The GL: the posting and its reversal both stand, netting to nothing.
    rid = out['receipt_id']
    assert GlJournal.objects.filter(source_model='receipt', source_id=rid).count() == 2
    assert GlJournal.objects.filter(source_model='receipt_reversal', source_id=rid).count() == 2
    for account in (STING_EXPENSE, STING_PAYABLE):
        assert _net('receipt', rid, account) + _net('receipt_reversal', rid, account) == 0

    # The payable: kept, closed, nothing owed, out of aged payables.
    receipt = Receipt.objects.get(pk=rid)
    assert receipt.status == 'canceled' and receipt.dt_journaled
    assert float(receipt.totals['balance']) == 0.0 and float(receipt.totals['adjusted']) == 100.0
    ledger = Ledger.objects.get(parent_id=rid, model_name='receipt')
    assert (ledger.value_original, ledger.value_available) == (Decimal('100.00'), 0)
    assert ('contact', filer.pk) not in _payees()
    action = Action.objects.get(pk=out['action_id'])
    assert action.status == 'canceled'
    assert action.metadata['review']['state'] == 'rejected'
    assert action.metadata['review']['note'] == 'No breach on the footage'

    # Nothing is paid on a rejected sting.
    r = filer_client.post(f'/wcapi/receipt/{rid}/add_cash/', {'amount': '1.00', 'method': 'cash'},
                          content_type='application/json')
    assert r.status_code == 409 and 'rejected' in r.json()['message']


def test_a_sting_that_needs_no_review_cannot_be_reviewed(filer, classes):
    from apps.accounts.services.small_sting import reject_small_sting
    from apps.core.services.door import Refused
    out = _file(filer, sting_class_key='inconvenience')
    with pytest.raises(Refused) as e:
        reject_small_sting(_actor(filer), action_id=out['action_id'], reason='x')
    assert e.value.code == 'sting_not_under_review'


def test_a_portal_user_cannot_approve_or_reject(filer, classes, django_user_model, client):
    from apps.accounts.services.small_sting import approve_small_sting, reject_small_sting
    from apps.core.models import Action
    from apps.core.services.door import Refused
    from apps.orgs.models import OrgBase
    org = OrgBase.objects.create(company='Portal Co', org_type='customer', is_active=True)
    customer = django_user_model.objects.create_user(email='portal2@sting.test', password='x',
                                                     username='', role='customer', customer=org)
    out = _file(customer, sting_class_key='safety_breach')
    for review, kw in ((approve_small_sting, {}), (reject_small_sting, {'reason': 'mine'})):
        with pytest.raises(Refused) as e:
            review(_actor(customer), action_id=out['action_id'], **kw)
        assert e.value.code == 'sting_reviewer'
    client.force_login(customer)
    r = client.post('/wcapi/_manage/', {'action': 'approve_small_sting',
                                        'params': {'action_id': out['action_id']}},
                    content_type='application/json')
    assert r.status_code == 403, r.content
    assert Action.objects.get(pk=out['action_id']).metadata['review']['state'] == 'pending'


def test_filing_with_a_class_through_manage(filer_client, filer, classes):
    r = filer_client.post('/wcapi/_manage/', {'action': 'file_small_sting',
                                              'params': {'complaint': 'Pod left with door open',
                                                         'class': 'safety_breach'}},
                          content_type='application/json')
    assert r.status_code == 200, r.content
    data = r.json()['data']
    assert (data['amount'], data['review'], data['term']) == (100.0, 'pending', 'N10')
    assert 'under review' in data['message']
