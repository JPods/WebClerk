"""The chart reads the way an accountant expects and teaches the way a beginner needs.

Bill, 2026-09-23: "a nice looking set of gl accounts that will please accountants and
make teaching small business people accounting relatively easy."
"""
import pytest

from apps.accounts.choices import GL_ACCOUNT_CATEGORY_CHOICES, GL_ACCOUNT_TYPE_CHOICES
from apps.accounts.management.commands.seed_gl_accounts import ACCOUNTS, GL_DEFAULTS, REPLACED
from apps.accounts.services.chart import NORMAL_BALANCE, ROLES, SECTIONS

# The thousands digit says what family an account belongs to.
FAMILY = {'1': {'asset', 'contra_asset'}, '2': {'liability'}, '3': {'equity', 'contra_equity'},
          '4': {'revenue', 'contra_revenue'}, '5': {'cost_of_sales'}, '6': {'expense'},
          '7': {'other_income', 'other_expense'}}


@pytest.mark.parametrize('ida,name,typ,cat,used_for,summary', ACCOUNTS, ids=[a[0] for a in ACCOUNTS])
def test_each_account_is_numbered_typed_placed_and_explained(ida, name, typ, cat, used_for, summary):
    assert typ in FAMILY[ida[0]], f'{ida} is numbered as {ida[0]}xxx but typed {typ}'
    assert typ in NORMAL_BALANCE and cat in SECTIONS
    assert name and len(summary) > 40, 'every account says what belongs in it'


def test_every_type_and_section_in_the_model_is_accounted_for():
    assert {v for v, _ in GL_ACCOUNT_TYPE_CHOICES if v} == set(NORMAL_BALANCE)
    assert {v for v, _ in GL_ACCOUNT_CATEGORY_CHOICES} == set(SECTIONS)


def test_codes_are_unique_and_every_role_is_mapped_to_one():
    codes = [a[0] for a in ACCOUNTS]
    assert len(codes) == len(set(codes))
    assert set(GL_DEFAULTS) == set(ROLES)
    assert set(GL_DEFAULTS.values()) <= set(codes)


def test_replaced_accounts_are_gone_and_their_successors_exist():
    codes = {a[0] for a in ACCOUNTS}
    assert not codes & set(REPLACED)
    assert set(REPLACED.values()) <= codes


@pytest.mark.django_db
def test_retiring_an_account_moves_every_reference_to_its_successor(chart_of_accounts):
    from django.core.management import call_command
    from apps.accounts.models import GlAccount, GlJournal
    from apps.core.models import Setting
    from tests.conftest import ItemFactory

    GlAccount.objects.create(ida='6960-writeoff', name='Old write-off', type='expense',
                             category='operating_expenses', is_active=True)
    journal = GlJournal.objects.create(ida='zz-old', account='6960-writeoff', debit=5.0)
    item = ItemFactory()
    type(item).objects.filter(pk=item.pk).update(gls={'expense': '6960-writeoff'})
    company = Setting.objects.get(purpose='wc:company_profile')
    Setting.objects.filter(pk=company.pk).update(
        config={**company.config, 'gl_defaults': {**company.config['gl_defaults'],
                                                  'bad_debt_writeoff': '6960-writeoff'}})

    call_command('retire_gl_accounts', '--apply', verbosity=0)

    assert not GlAccount.objects.filter(ida='6960-writeoff').exists()
    journal.refresh_from_db(), item.refresh_from_db()
    assert journal.account == '6500-bad_debt'
    assert item.gls['expense'] == '6500-bad_debt'
    assert Setting.objects.get(pk=company.pk).config['gl_defaults']['bad_debt_writeoff'] == '6500-bad_debt'


@pytest.mark.django_db
def test_retire_without_apply_changes_nothing(chart_of_accounts):
    from django.core.management import call_command
    from apps.accounts.models import GlAccount

    GlAccount.objects.create(ida='6960-writeoff', name='Old', type='expense',
                             category='operating_expenses', is_active=True)
    call_command('retire_gl_accounts', verbosity=0)
    assert GlAccount.objects.filter(ida='6960-writeoff').exists()
