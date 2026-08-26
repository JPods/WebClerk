"""Tests for accounting dashboard data service."""
import pytest


@pytest.mark.django_db
class TestAccountingDashboard:

    def test_dashboard_returns_all_sections(self):
        """Dashboard returns all required data sections."""
        from apps.accounts.services.accounting_dashboard import get_accounting_dashboard

        data = get_accounting_dashboard()
        assert 'journal_status' in data
        assert 'gl_balance' in data
        assert 'transaction_volume' in data
        assert 'locked_records' in data
        assert 'aging_summary' in data
        assert 'pending_inventory' in data
        assert 'dt_generated' in data

    def test_gl_balance_structure(self):
        """GL balance section has correct fields."""
        from apps.accounts.services.accounting_dashboard import get_accounting_dashboard

        data = get_accounting_dashboard()
        gl = data['gl_balance']
        assert 'total_debit' in gl
        assert 'total_credit' in gl
        assert 'imbalance' in gl
        assert 'balanced' in gl
        assert isinstance(gl['balanced'], bool)

    def test_transaction_volume_by_type(self):
        """Transaction volume includes counts by type."""
        from apps.accounts.services.accounting_dashboard import get_accounting_dashboard
        from tests.conftest import OrderFactory, InvoiceFactory

        OrderFactory()
        InvoiceFactory()

        data = get_accounting_dashboard()
        vol = data['transaction_volume']
        assert 'order' in vol
        assert 'invoice' in vol
        assert vol['order']['total'] >= 1
        assert vol['invoice']['total'] >= 1

    def test_pending_inventory_structure(self):
        """Pending inventory section has count and age."""
        from apps.accounts.services.accounting_dashboard import get_accounting_dashboard

        data = get_accounting_dashboard()
        pending = data['pending_inventory']
        assert 'unprocessed_count' in pending
        assert 'oldest_age_minutes' in pending
        assert isinstance(pending['unprocessed_count'], int)

    def test_manage_action_works(self):
        """Dashboard accessible via manage action dispatch."""
        from apps.core.views.manage_view import _ACTION_DISPATCH

        handler = _ACTION_DISPATCH.get('get_accounting_dashboard')
        assert handler is not None
        result = handler({})
        # Commerce dashboard version returns ar + payments (not journal_status)
        assert 'ar' in result or 'journal_status' in result

    def test_locked_records_structure(self):
        """Locked records section shows locked vs unlocked counts."""
        from apps.accounts.services.accounting_dashboard import get_accounting_dashboard

        data = get_accounting_dashboard()
        locked = data['locked_records']
        assert 'invoice' in locked
        assert 'locked' in locked['invoice']
        assert 'unlocked' in locked['invoice']

    def test_aging_summary_structure(self):
        """Aging summary has period buckets and total AR."""
        from apps.accounts.services.accounting_dashboard import get_accounting_dashboard

        data = get_accounting_dashboard()
        aging = data['aging_summary']
        assert 'current' in aging
        assert 'period_1_30' in aging
        assert 'period_2_60' in aging
        assert 'period_3_90_plus' in aging
        assert 'total_ar' in aging
        assert 'customers_with_balance' in aging
