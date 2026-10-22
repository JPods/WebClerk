"""A Small-Sting creates a payable (Bill, 2026-10-22).

- $1.72 unless the sting names its value; a P&L event.
- Owed to the person who filed it, never their org.
- Dr 6550-small_sting_expense / Cr 2230-small_stings_payable.
- Paid in cash like any payable (Dr 2230 / Cr cash); it ages in aged payables until then.

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
    migration = importlib.import_module('apps.accounts.migrations.0018_ledger_contact_small_sting_accounts')
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
