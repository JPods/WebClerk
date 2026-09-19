"""Tests for the post_gl_entries manage action.

Validates the user-initiated GL posting workflow:
  POST /wcapi/_manage/ { action: "post_gl_entries", params: { model_name, id } }
"""
import pytest
from tests.conftest import InvoiceFactory


def invoice_with_line(unit=500.0, qty=1):
    """An invoice a user could have made: one line, no tax, no shipping."""
    from apps.transactions.models import InvoiceLine
    invoice = InvoiceFactory()
    InvoiceLine.objects.create(invoice=invoice, quantity={'active': qty},
                               price={'unit': unit, 'precision': 2}, cost={'unit': 0})
    invoice.refresh_from_db()
    return invoice


@pytest.mark.django_db
@pytest.mark.usefixtures("chart_of_accounts")
class TestPostGLManageAction:

    def test_posts_and_locks_invoice(self):
        """Post GL entries for an invoice → entries created, record locked."""
        from apps.core.views.manage_view import _post_gl_entries
        from apps.accounts.models import GlJournal

        invoice = invoice_with_line(500.0)

        result = _post_gl_entries({'model_name': 'invoice', 'id': invoice.pk})

        assert result['posted'] == 2
        assert result['locked'] is True
        assert GlJournal.objects.filter(source_id=invoice.pk).count() == 2

        # Verify record is actually locked in DB
        invoice.refresh_from_db()
        assert invoice.is_locked is True

    def test_locked_record_rejected(self):
        """Already-locked record raises ValueError."""
        from apps.core.views.manage_view import _post_gl_entries

        invoice = InvoiceFactory()
        invoice.__class__.objects.filter(pk=invoice.pk).update(is_locked=True)

        with pytest.raises(ValueError, match="already journalized"):
            _post_gl_entries({'model_name': 'invoice', 'id': invoice.pk})

    def test_double_post_returns_zero(self):
        """Second post attempt returns 0 entries (already posted)."""
        from apps.core.views.manage_view import _post_gl_entries

        invoice = invoice_with_line(100.0)

        result1 = _post_gl_entries({'model_name': 'invoice', 'id': invoice.pk})
        assert result1['posted'] == 2

        # Unlock to allow retry attempt (normally wouldn't happen)
        invoice.__class__.objects.filter(pk=invoice.pk).update(is_locked=False)

        result2 = _post_gl_entries({'model_name': 'invoice', 'id': invoice.pk})
        assert result2['posted'] == 0  # duplicate guard

    def test_missing_params_raises(self):
        from apps.core.views.manage_view import _post_gl_entries

        with pytest.raises(ValueError, match="required"):
            _post_gl_entries({})

    def test_invalid_model_raises(self):
        from apps.core.views.manage_view import _post_gl_entries

        with pytest.raises(ValueError, match="must be"):
            _post_gl_entries({'model_name': 'order', 'id': 1})


@pytest.mark.django_db
@pytest.mark.usefixtures("chart_of_accounts")
class TestReverseGLManageAction:
    """Reverse GL entries — contra entries, unlock record."""

    def _journalize(self, invoice):
        """Post an invoice through the one GL engine (from its own lines)."""
        from apps.core.views.manage_view import _post_gl_entries
        return _post_gl_entries({'model_name': 'invoice', 'id': invoice.pk})

    def test_reversal_creates_contra_entries(self):
        """Reversal swaps debit↔credit, same amounts."""
        from apps.core.views.manage_view import _reverse_gl_entries
        from apps.accounts.models import GlJournal

        invoice = invoice_with_line(500.0)
        self._journalize(invoice)

        result = _reverse_gl_entries({'model_name': 'invoice', 'id': invoice.pk})
        assert result['reversed'] == 2

        # Should now have 4 entries: 2 original + 2 reversal
        all_entries = GlJournal.objects.filter(source_id=invoice.pk)
        assert all_entries.count() == 4

        # Originals: debit 1200, credit 4000
        originals = all_entries.filter(source_model='invoice')
        assert originals.count() == 2

        # Reversals: credit 1200, debit 4000 (swapped)
        reversals = all_entries.filter(source_model='invoice_reversal')
        assert reversals.count() == 2

        # Net should be zero
        from django.db.models import Sum
        totals = all_entries.aggregate(d=Sum('debit'), c=Sum('credit'))
        assert totals['d'] == totals['c']

    def test_reversal_unlocks_record(self):
        """After reversal, record is unlocked for editing."""
        from apps.core.views.manage_view import _reverse_gl_entries

        invoice = invoice_with_line(500.0)
        self._journalize(invoice)

        invoice.refresh_from_db()
        assert invoice.is_locked is True

        _reverse_gl_entries({'model_name': 'invoice', 'id': invoice.pk})

        invoice.refresh_from_db()
        assert invoice.is_locked is False

    def test_double_reversal_blocked(self):
        """Can't reverse the same entries twice."""
        from apps.core.views.manage_view import _reverse_gl_entries

        invoice = invoice_with_line(500.0)
        self._journalize(invoice)

        result1 = _reverse_gl_entries({'model_name': 'invoice', 'id': invoice.pk})
        assert result1['reversed'] == 2

        # Re-lock to allow second attempt
        invoice.__class__.objects.filter(pk=invoice.pk).update(is_locked=True)

        result2 = _reverse_gl_entries({'model_name': 'invoice', 'id': invoice.pk})
        assert result2['reversed'] == 0

    def test_unlocked_record_rejected(self):
        """Can't reverse a record that isn't journalized."""
        from apps.core.views.manage_view import _reverse_gl_entries

        invoice = InvoiceFactory()
        with pytest.raises(ValueError, match="not journalized"):
            _reverse_gl_entries({'model_name': 'invoice', 'id': invoice.pk})

    def test_full_cycle_post_reverse_repost(self):
        """Post → Reverse → Edit → Re-post: the complete correction workflow."""
        from apps.core.views.manage_view import _post_gl_entries, _reverse_gl_entries
        from apps.accounts.models import GlJournal

        invoice = invoice_with_line(500.0)
        self._journalize(invoice)
        assert GlJournal.objects.filter(source_id=invoice.pk).count() == 2

        # Reverse
        _reverse_gl_entries({'model_name': 'invoice', 'id': invoice.pk})
        assert GlJournal.objects.filter(source_id=invoice.pk).count() == 4

        invoice.refresh_from_db()
        assert invoice.is_locked is False

        # Edit the invoice as a user would: change the line's price
        line = invoice.lines.first()
        line.price = {**line.price, 'unit': 700.0}
        line.save()
        invoice.refresh_from_db()
        assert invoice.totals['total'] == 700.0

        # Re-post. The originals stay as permanent record; the guard counts
        # unreversed rows, so a reversed invoice can be corrected and posted again.
        result = _post_gl_entries({'model_name': 'invoice', 'id': invoice.pk})
        assert result['posted'] == 2
        assert result['locked'] is True

        # 2 originals + 2 reversals + 2 new originals
        originals = GlJournal.objects.filter(source_id=invoice.pk, source_model='invoice')
        assert originals.count() == 4
        assert originals.filter(debit=700.0).count() == 1
