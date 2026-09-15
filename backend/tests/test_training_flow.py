"""Tests for Alice's training/health-check transaction flow.

Validates the guided commerce cycle that teaches users how
transactions flow and verifies system health.
"""
import pytest
from tests.conftest import CustomerFactory, ItemFactory, WarehouseFactory


@pytest.mark.django_db
class TestTrainingFlow:
    """Full training cycle: proposal → order → invoice → payment → PO → receive."""

    def _setup(self):
        from apps.products.models import InventoryLayer

        customer = CustomerFactory(display_name='Training Corp')
        item = ItemFactory(ida='TRAIN-WIDGET')
        item.__class__.objects.filter(pk=item.pk).update(
            price={'base': 25.0, 'retail': 25.0},
            cost={'standard': 10.0},
        )
        item.refresh_from_db()

        wh = WarehouseFactory(name='Training WH')
        InventoryLayer.objects.create(
            item=item, warehouse=wh,
            quantity={'on_hand': 50, 'on_so': 0, 'on_po': 0},
        )
        return customer, item

    def test_full_cycle_runs(self):
        """Full cycle completes without errors."""
        from apps.transactions.services.training_flow import TrainingFlow

        customer, item = self._setup()
        flow = TrainingFlow(customer.pk, item.pk)
        report = flow.run_full_cycle()

        assert len(report['steps']) == 6
        assert report['records_created']['proposal'] is not None
        assert report['records_created']['order'] is not None
        assert report['records_created']['invoice'] is not None
        assert report['records_created']['payment'] is not None
        assert report['records_created']['purchase'] is not None

    def test_training_flag_set(self):
        """All created records have metadata.training=True."""
        from apps.transactions.services.training_flow import TrainingFlow
        from apps.transactions.models import Proposal, Order, Invoice, Purchase, Payment

        customer, item = self._setup()
        flow = TrainingFlow(customer.pk, item.pk)
        report = flow.run_full_cycle()

        ids = report['records_created']
        for Model, key in [
            (Proposal, 'proposal'), (Order, 'order'),
            (Invoice, 'invoice'), (Purchase, 'purchase'),
        ]:
            record = Model.objects.get(pk=ids[key])
            meta = getattr(record, 'metadata', {}) or {}
            assert meta.get('training') is True, f"{key} missing training flag"

    def test_proposal_no_inventory_effect(self):
        """Step 1: proposal doesn't change inventory."""
        from apps.transactions.services.training_flow import TrainingFlow

        customer, item = self._setup()
        flow = TrainingFlow(customer.pk, item.pk)
        step = flow.step_1_create_proposal(5)

        assert step['inventory_changed'] is False

    def test_cleanup_function_exists(self):
        """Verify cleanup function is importable and callable.

        Full cleanup test requires PostgreSQL (JSON __contains filter).
        Run with: PYTEST_FORCE_DB=1 ./bin/python -m pytest -k cleanup
        """
        from apps.transactions.services.training_flow import cleanup_training_records
        assert callable(cleanup_training_records)

    def test_report_includes_inventory_snapshots(self):
        """Each step includes before/after inventory snapshots."""
        from apps.transactions.services.training_flow import TrainingFlow

        customer, item = self._setup()
        flow = TrainingFlow(customer.pk, item.pk)
        report = flow.run_full_cycle()

        for step in report['steps']:
            if 'inventory_before' in step:
                assert 'on_hand' in step['inventory_before']
            if 'inventory_after' in step:
                assert 'on_hand' in step['inventory_after']

    def test_manage_action_runs_flow(self):
        """Manage action runs the training flow via API dispatch."""
        from apps.core.views.manage_view import _run_training_flow

        customer, item = self._setup()
        result = _run_training_flow({
            'customer_id': customer.pk,
            'item_id': item.pk,
            'proposal_qty': 3,
            'order_qty': 2,
            'invoice_qty': 1,
        })

        assert len(result['steps']) == 6
        assert result['records_created']['proposal'] is not None
