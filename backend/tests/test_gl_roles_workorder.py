"""Step 3 GL roles (Bill, 2026-09-22): workorders post to four roles users map themselves.

work_in_process, labor_applied (clearing: labor is an estimate WebClerk never stocks),
inventory_cost_variance (deficit true-up) and labor_variance (accounting's reconcile).
Scrap uses the existing scrap role. The demo chart maps them to 1210/2160/5310/5320.
~/Allie/readmes/assessments/2026-09-20/step3-workorders-plan.md §1a, §1b
"""
import pytest

from apps.accounts.services.chart import role_account

pytestmark = pytest.mark.django_db

NEW_ROLES = {
    'work_in_process': '1210-work_in_process',
    'labor_applied': '2160-labor_applied',
    'inventory_cost_variance': '5310-inventory_cost_variance',
    'labor_variance': '5320-labor_variance',
}


def test_each_workorder_role_resolves_to_a_chart_account(chart_of_accounts):
    for role, code in NEW_ROLES.items():
        assert role_account(role) == code


def test_each_workorder_account_takes_a_posting(chart_of_accounts):
    from apps.accounts.models.gl_journal import GlJournal
    for code in NEW_ROLES.values():
        GlJournal.objects.create(account=code, source_model='test', source_id=1)
    assert GlJournal.objects.filter(account__in=NEW_ROLES.values()).count() == 4


def test_an_items_variance_account_defaults_to_the_cost_variance_role(chart_of_accounts):
    from apps.accounts.services.gl_defaults import get_item_gl_defaults
    assert get_item_gl_defaults()['variance'] == '5310-inventory_cost_variance'


def test_a_user_can_map_a_role_to_their_own_account(chart_of_accounts):
    """Users set their own accounts: the demo codes are defaults, never hardcoded."""
    from apps.core.models import Setting
    company = Setting.objects.get(purpose='wc:company_profile')
    company.config = {**company.config,
                      'gl_defaults': {**company.config['gl_defaults'], 'labor_applied': '2200-accrued_liabilities'}}
    company._setting_update_authorized = True
    company.save()
    assert role_account('labor_applied') == '2200-accrued_liabilities'
