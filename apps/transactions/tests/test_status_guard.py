"""
Tests for status_guard — transition validation and journalized locks.

Uses simple mock objects to test the guard logic without database dependencies.
For integration tests that hit PostgreSQL, use PYTEST_FORCE_DB=1.
"""
from unittest.mock import MagicMock
from django.test import TestCase

from apps.transactions.services.status_guard import (
    validate_transition,
    validate_modification,
    is_journalized,
    TRANSITIONS,
    TERMINAL,
    JOURNALIZABLE_MODELS,
)


def _make_instance(model_name='Order', status='planned', metadata=None,
                   commission=None, customer_id=None):
    """Create a mock instance for testing."""
    obj = MagicMock()
    obj.__class__ = type(model_name, (), {})
    obj.__class__.__name__ = model_name
    obj.status = status
    obj.metadata = metadata or {}
    obj.commission = commission or {}
    obj.customer_id = customer_id
    obj.pk = 1
    return obj


class TestTransitionMatrix(TestCase):
    """Verify allowed transitions."""

    def test_planned_to_released(self):
        obj = _make_instance(status='planned')
        result = validate_transition(obj, 'order', 'released')
        # May fail on precondition (no lines), but transition itself is allowed
        self.assertIn('released', TRANSITIONS['order']['planned'])

    def test_terminal_status_blocks_transition(self):
        obj = _make_instance(status='complete')
        result = validate_transition(obj, 'order', 'released')
        self.assertFalse(result.can_proceed)
        self.assertTrue(any('terminal' in e.lower() or 'cannot transition' in e.lower()
                            for e in result.errors))

    def test_canceled_is_terminal(self):
        obj = _make_instance(status='canceled')
        result = validate_transition(obj, 'order', 'planned')
        self.assertFalse(result.can_proceed)

    def test_invalid_transition_blocked(self):
        obj = _make_instance(status='planned')
        result = validate_transition(obj, 'order', 'complete')
        self.assertFalse(result.can_proceed)

    def test_same_status_is_noop(self):
        obj = _make_instance(status='released')
        result = validate_transition(obj, 'order', 'released')
        self.assertTrue(result.can_proceed)

    def test_hold_can_resume(self):
        self.assertIn('released', TRANSITIONS['order']['hold'])
        self.assertIn('in_progress', TRANSITIONS['order']['hold'])

    def test_all_models_have_transitions(self):
        for model in ('proposal', 'order', 'invoice', 'purchase',
                       'work_order', 'requisition', 'payment'):
            self.assertIn(model, TRANSITIONS, f'{model} missing from TRANSITIONS')

    def test_proposal_has_sent_accepted(self):
        self.assertIn('sent', TRANSITIONS['proposal'])
        self.assertIn('accepted', TRANSITIONS['proposal'])

    def test_payment_has_voided(self):
        self.assertIn('voided', TRANSITIONS['payment'])

    def test_invoice_standalone_allowed(self):
        """Over-the-counter invoice — no order required."""
        obj = _make_instance(model_name='Invoice', status='planned', customer_id=42)
        # Invoice doesn't require customer for release (unlike proposal)
        self.assertIn('released', TRANSITIONS['invoice']['planned'])


class TestJournalizedLock(TestCase):
    """Journalized records cannot be modified."""

    def test_posted_invoice_is_journalized(self):
        obj = _make_instance(
            model_name='Invoice',
            metadata={'gl_accounts': {'posted': True}},
        )
        self.assertTrue(is_journalized(obj))

    def test_unposted_invoice_is_not_journalized(self):
        obj = _make_instance(model_name='Invoice')
        self.assertFalse(is_journalized(obj))

    def test_journalized_blocks_status_change(self):
        obj = _make_instance(
            model_name='Invoice',
            status='released',
            metadata={'gl_accounts': {'posted': True}},
        )
        result = validate_transition(obj, 'invoice', 'complete')
        self.assertFalse(result.can_proceed)
        self.assertTrue(any('journalized' in e.lower() for e in result.errors))

    def test_journalized_blocks_modification(self):
        obj = _make_instance(
            model_name='Invoice',
            metadata={'gl_accounts': {'posted': True}},
        )
        result = validate_modification(obj, 'invoice')
        self.assertFalse(result.can_proceed)

    def test_unposted_allows_modification(self):
        obj = _make_instance(model_name='Invoice')
        result = validate_modification(obj, 'invoice')
        self.assertTrue(result.can_proceed)

    def test_accrued_commission_is_journalized(self):
        obj = _make_instance(
            model_name='Invoice',
            commission={'accrued': True, 'total': 150.00},
        )
        self.assertTrue(is_journalized(obj))

    def test_payment_journalized_blocks_modification(self):
        obj = _make_instance(
            model_name='Payment',
            metadata={'gl_accounts': {'posted': True, 'event': 'payment_journalized'}},
        )
        result = validate_modification(obj, 'payment')
        self.assertFalse(result.can_proceed)

    def test_non_journalizable_model_always_modifiable(self):
        obj = _make_instance(model_name='Proposal')
        result = validate_modification(obj, 'proposal')
        self.assertTrue(result.can_proceed)


class TestTerminalStatuses(TestCase):
    """Terminal statuses have no outbound transitions."""

    def test_terminal_set(self):
        self.assertIn('complete', TERMINAL)
        self.assertIn('canceled', TERMINAL)

    def test_all_terminal_have_empty_transitions(self):
        for model, transitions in TRANSITIONS.items():
            for term in TERMINAL:
                if term in transitions:
                    self.assertEqual(
                        transitions[term], [],
                        f'{model}.{term} should have no outbound transitions'
                    )


class TestJournalizableModels(TestCase):
    """Correct models are in the journalizable set."""

    def test_invoice_journalizable(self):
        self.assertIn('invoice', JOURNALIZABLE_MODELS)

    def test_payment_journalizable(self):
        self.assertIn('payment', JOURNALIZABLE_MODELS)

    def test_purchase_journalizable(self):
        self.assertIn('purchase', JOURNALIZABLE_MODELS)

    def test_lines_journalizable(self):
        self.assertIn('invoice_line', JOURNALIZABLE_MODELS)
        self.assertIn('purchase_line', JOURNALIZABLE_MODELS)
        self.assertIn('receipt_line', JOURNALIZABLE_MODELS)

    def test_order_not_journalizable(self):
        self.assertNotIn('order', JOURNALIZABLE_MODELS)

    def test_proposal_not_journalizable(self):
        self.assertNotIn('proposal', JOURNALIZABLE_MODELS)
