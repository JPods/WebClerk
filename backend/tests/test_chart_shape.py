"""The chart reads the way an accountant expects and teaches the way a beginner needs.

Bill, 2026-09-23: "a nice looking set of gl accounts that will please accountants and
make teaching small business people accounting relatively easy."

Bill, 2026-10-30: one standard chart file, loaded like any other bundle, and only into a new
database; once operating, the company changes its own records.
"""
import pytest

from apps.accounts.choices import GL_ACCOUNT_CATEGORY_CHOICES, GL_ACCOUNT_TYPE_CHOICES
from apps.accounts.services.chart import (NORMAL_BALANCE, SECTIONS, chart_defects, install,
                                          standard_chart)

STANDARD = standard_chart()

# The thousands digit says what family an account belongs to.
FAMILY = {'1': {'asset', 'contra_asset'}, '2': {'liability'}, '3': {'equity', 'contra_equity'},
          '4': {'revenue', 'contra_revenue'}, '5': {'cost_of_sales'}, '6': {'expense'},
          '7': {'other_income', 'other_expense'}}


@pytest.mark.parametrize('acct', STANDARD['accounts'], ids=[a['ida'] for a in STANDARD['accounts']])
def test_each_account_is_numbered_typed_placed_and_explained(acct):
    ida, typ = acct['ida'], acct['type']
    assert typ in FAMILY[ida[0]], f'{ida} is numbered as {ida[0]}xxx but typed {typ}'
    assert acct['name'] and len(acct.get('summary') or '') > 40, 'every account says what belongs in it'


def test_every_type_and_section_in_the_model_is_accounted_for():
    assert {v for v, _ in GL_ACCOUNT_TYPE_CHOICES if v} == set(NORMAL_BALANCE)
    assert {v for v, _ in GL_ACCOUNT_CATEGORY_CHOICES} == set(SECTIONS)


def test_the_standard_chart_installs_whole():
    """Unique codes, known types and sections, every posting role mapped into the chart."""
    assert chart_defects(STANDARD) == []


@pytest.mark.django_db
def test_a_new_database_gets_the_chart_and_role_map_as_one_bundle(tmp_path, settings):
    from apps.accounts.models import GlAccount
    from apps.core.models import Setting
    from apps.core.services import bundle_import
    from apps.sync.models.bundle import Bundle
    settings.WORK_DIR = tmp_path
    company = Setting.objects.filter(purpose='wc:company_profile', is_active=True).first()
    if company is None:
        company = Setting(ida='company-profile', name='Company Profile', purpose='wc:company_profile',
                          scope='system', config={})
        company._setting_create_authorized = True
        company.save()

    result = bundle_import.run('chart_standard', STANDARD, source='test', load='chart')

    assert result['errors'] == [] and Bundle.objects.get(pk=result['bundle_id']).status == 'completed'
    assert GlAccount.objects.count() == len(STANDARD['accounts'])
    company.refresh_from_db()
    assert {k: v for k, v in company.config['gl_defaults'].items() if k != 'note'} == STANDARD['roles']

    # Operating now: the file never touches the company's chart again.
    again = bundle_import.run('chart_standard', STANDARD, source='test', load='chart')
    assert 'already has a chart' in again['errors'][0]
    assert Bundle.objects.get(pk=again['bundle_id']).status == 'defects'


@pytest.mark.django_db
def test_a_defective_chart_writes_nothing():
    from apps.accounts.models import GlAccount
    broken = {**STANDARD, 'roles': {**STANDARD['roles'], 'sales_revenue': '4999-nowhere'}}

    result = install(broken)

    assert result['errors'] == ["role sales_revenue: '4999-nowhere' is not an account in this chart"]
    assert not GlAccount.objects.exists()
