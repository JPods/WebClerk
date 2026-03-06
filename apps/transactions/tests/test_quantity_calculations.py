"""Tests for quantity calculation and normalization.

These tests verify the quantity semantics described in:
  readmes/topics/transactions/transactions-totals.md

=== QUANTITY RULES (Updated 2026-03-05) ===

1. USER INPUT
   - User always enters `active` as the primary quantity input
   - System mirrors: `staged = active` for standalone lines

2. STANDALONE LINES (user creates new line, no parent)
   +-----------------+------------+---------+-----------+
   | Transaction     | active | staged  | remaining |
   +-----------------+------------+---------+-----------+
   | Order/Proposal  | 10         | 10      | 10        |  ← full qty available
   | Purchase        | 10         | 10      | 10        |  ← full qty available
   | Invoice/Receipt | 10         | 10      | 0         |  ← end of chain
   +-----------------+------------+---------+-----------+

3. TRANSFERRED LINES (created from parent via transfer service)
   +-----------------+------------+---------+-----------+
   | Transaction     | active | staged  | remaining |
   +-----------------+------------+---------+-----------+
   | Order (from prop)| 10        | 10      | 10        |  ← from source.remaining
   | Invoice (from ord)| 10       | 10      | 0         |  ← end of chain
   +-----------------+------------+---------+-----------+

4. TRANSFER EQUATION
   target.staged = transfer_qty  (from source.remaining)
   source.remaining -= transfer_qty

5. REMAINING CALCULATION (non-end-of-chain)
   - Standalone (staged == active): remaining = staged
   - After transfers consume qty: remaining = staged - consumed_by_transfers
"""

import pytest
from decimal import Decimal
from apps.transactions.models.base_line_model import (
    normalize_quantity_map,
    default_quantity,
    _is_end_of_chain,
)


class TestDefaultQuantity:
    """Test default_quantity() factory function."""

    def test_proposal_defaults(self):
        qty = default_quantity("proposal")
        assert qty["staged"] == 0
        assert qty["active"] == 0
        assert qty["remaining"] == 0
        assert qty["is_fixed"] is False
        assert qty["precision"] == 2

    def test_order_defaults(self):
        qty = default_quantity("order")
        assert qty["staged"] == 0
        assert qty["active"] == 0
        assert qty["remaining"] == 0

    def test_invoice_defaults(self):
        qty = default_quantity("invoice")
        assert qty["staged"] == 0
        assert qty["active"] == 0
        assert qty["remaining"] == 0

    def test_unknown_type_defaults(self):
        qty = default_quantity("unknown")
        assert qty["staged"] is None
        assert qty["active"] is None
        assert qty["remaining"] is None

    def test_receipt_defaults(self):
        """Receipt (end-of-chain) should have standard defaults."""
        qty = default_quantity("receipt")
        assert qty["staged"] == 0
        assert qty["active"] == 0
        assert qty["remaining"] == 0
        assert qty["precision"] == 2


class TestIsEndOfChain:
    """Test _is_end_of_chain() helper."""

    def test_invoice_is_end_of_chain(self):
        assert _is_end_of_chain("invoice") is True
        assert _is_end_of_chain("Invoice") is True
        assert _is_end_of_chain("invoice_line") is True

    def test_receipt_is_end_of_chain(self):
        """Receipt should be end-of-chain (nothing downstream from receipts)."""
        assert _is_end_of_chain("receipt") is True

    def test_order_not_end_of_chain(self):
        assert _is_end_of_chain("order") is False
        assert _is_end_of_chain("order_line") is False

    def test_proposal_not_end_of_chain(self):
        assert _is_end_of_chain("proposal") is False

    def test_purchase_not_end_of_chain(self):
        assert _is_end_of_chain("purchase") is False


class TestNormalizeQuantityMap:
    """Test normalize_quantity_map() normalization function."""

    # -- Basic normalization tests --

    def test_none_input_returns_default(self):
        """None input should return full defaults."""
        result = normalize_quantity_map(None, "order")
        assert result["staged"] == 0
        assert result["active"] == 0
        assert result["remaining"] == 0

    def test_empty_dict_returns_default(self):
        """Empty dict should return full defaults."""
        result = normalize_quantity_map({}, "order")
        assert result["staged"] == 0
        assert result["active"] == 0
        assert result["remaining"] == 0

    # -- Standard remaining calculation (non-invoice) --

    def test_remaining_calculated_from_staged_minus_active(self):
        """For non-invoice: remaining = staged - active."""
        result = normalize_quantity_map(
            {"staged": 10, "active": 3},
            "order"
        )
        assert result["remaining"] == 7.0

    def test_remaining_equals_staged_for_standalone(self):
        """Standalone (staged == active): remaining = staged (full qty available)."""
        result = normalize_quantity_map(
            {"staged": 10, "active": 10},
            "order"
        )
        # When staged == active, this is a standalone entry
        # remaining = staged (full qty available for downstream)
        assert result["remaining"] == 10.0

    def test_remaining_negative_when_over_processed(self):
        """remaining can be negative if active > staged."""
        result = normalize_quantity_map(
            {"staged": 10, "active": 15},
            "order"
        )
        assert result["remaining"] == -5.0

    # -- JSON deep-merge fix: partial updates should preserve existing values --

    def test_partial_update_active_preserves_staged(self):
        """When only active is updated, staged should be preserved from input."""
        result = normalize_quantity_map(
            {"staged": 10, "active": 5},
            "order"
        )
        assert result["staged"] == 10
        assert result["active"] == 5
        assert result["remaining"] == 5.0

    def test_partial_update_staged_preserves_active(self):
        """When only staged is updated, active should default to 0."""
        result = normalize_quantity_map(
            {"staged": 10},
            "order"
        )
        assert result["staged"] == 10
        assert result["active"] == 0
        assert result["remaining"] == 10.0

    # -- Invoice (end-of-chain) specific tests --

    def test_invoice_remaining_always_zero(self):
        """Invoice lines always have remaining = 0."""
        result = normalize_quantity_map(
            {"staged": 10, "active": 5},
            "invoice"
        )
        assert result["remaining"] == 0

    def test_invoice_staged_syncs_from_active(self):
        """If only active is set on invoice, staged should sync to match."""
        result = normalize_quantity_map(
            {"active": 5},
            "invoice"
        )
        assert result["staged"] == 5
        assert result["active"] == 5
        assert result["remaining"] == 0

    def test_invoice_active_syncs_from_staged(self):
        """If only staged is set on invoice (transfer), active should sync."""
        result = normalize_quantity_map(
            {"staged": 10},
            "invoice"
        )
        assert result["staged"] == 10
        assert result["active"] == 10
        assert result["remaining"] == 0

    # -- Receipt (end-of-chain) specific tests --

    def test_receipt_remaining_always_zero(self):
        """Receipt lines always have remaining = 0 (end-of-chain like invoice)."""
        result = normalize_quantity_map(
            {"staged": 10, "active": 5},
            "receipt"
        )
        assert result["remaining"] == 0

    def test_receipt_staged_syncs_from_active(self):
        """If only active is set on receipt, staged should sync to match."""
        result = normalize_quantity_map(
            {"active": 8},
            "receipt"
        )
        assert result["staged"] == 8
        assert result["active"] == 8
        assert result["remaining"] == 0

    # -- Control key tests --

    def test_is_fixed_preserved(self):
        """is_fixed should be preserved from input."""
        result = normalize_quantity_map(
            {"staged": 10, "is_fixed": True},
            "order"
        )
        assert result["is_fixed"] is True

    def test_precision_preserved(self):
        """precision should be preserved from input."""
        result = normalize_quantity_map(
            {"staged": 10, "precision": 4},
            "order"
        )
        assert result["precision"] == 4

    def test_is_blanket_preserved(self):
        """is_blanket should be preserved from input."""
        result = normalize_quantity_map(
            {"staged": 10, "is_blanket": True},
            "order"
        )
        assert result["is_blanket"] is True

    def test_increment_preserved(self):
        """increment should be preserved from input."""
        result = normalize_quantity_map(
            {"staged": 10, "increment": 5},
            "order"
        )
        assert result["increment"] == 5.0

    # -- Null handling tests --

    def test_null_staged_mirrors_active(self):
        """When staged is null but active is set, staged mirrors active (standalone)."""
        result = normalize_quantity_map(
            {"staged": None, "active": 5},
            "order"
        )
        # Standalone entry: active provided, staged mirrors
        assert result["staged"] == 5
        # Since staged == active, remaining = staged
        assert result["remaining"] == 5.0

    def test_null_active_defaults_to_zero(self):
        """Null active should default to 0."""
        result = normalize_quantity_map(
            {"staged": 10, "active": None},
            "order"
        )
        assert result["active"] == 0
        assert result["remaining"] == 10.0


@pytest.mark.django_db
class TestLineSaveQuantityNormalization:
    """Test that line.save() properly normalizes quantity via normalize_quantity_map."""

    def test_order_line_save_calculates_remaining(self):
        """OrderLine.save() should calculate remaining = staged - active."""
        from apps.transactions.models import Order, OrderLine
        from apps.products.models import Item

        # Create required objects
        item = Item.objects.create(name="Test Item", ida="TEST-001")
        order = Order.objects.create(status="draft")

        # Create line with partial quantity data
        line = OrderLine(
            order=order,
            item_fk=item,
            quantity={"staged": 10, "active": 3}
        )
        line.save()

        # Verify remaining was calculated
        line.refresh_from_db()
        assert line.quantity["remaining"] == 7.0

    def test_order_line_update_recalculates_remaining(self):
        """Updating active should recalculate remaining on save."""
        from apps.transactions.models import Order, OrderLine
        from apps.products.models import Item

        item = Item.objects.create(name="Test Item 2", ida="TEST-002")
        order = Order.objects.create(status="draft")

        # Create initial line
        line = OrderLine.objects.create(
            order=order,
            item_fk=item,
            quantity={"staged": 10, "active": 0, "remaining": 10}
        )

        # Update active
        line.quantity["active"] = 4
        line.save()

        line.refresh_from_db()
        assert line.quantity["remaining"] == 6.0

    def test_invoice_line_remaining_always_zero(self):
        """InvoiceLine remaining should always be 0."""
        from apps.transactions.models import Invoice, InvoiceLine
        from apps.products.models import Item

        item = Item.objects.create(name="Test Item 3", ida="TEST-003")
        invoice = Invoice.objects.create(status="draft")

        line = InvoiceLine(
            invoice=invoice,
            item_fk=item,
            quantity={"staged": 10, "active": 5}  # remaining should be ignored
        )
        line.save()

        line.refresh_from_db()
        assert line.quantity["remaining"] == 0
