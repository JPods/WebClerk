from apps.transactions.services.transaction_save import _line_staged_qty


def test_line_staged_qty_prefers_active_over_staged():
    qty = _line_staged_qty({"quantity": {"staged": 7, "active": 4}})
    assert qty == 4.0


def test_line_staged_qty_reads_active_only():
    """staged is a creation snapshot and placed/actioned are retired: no fallbacks."""
    assert _line_staged_qty({"quantity": {"staged": 7}}) == 0.0
    assert _line_staged_qty({"quantity": {"placed": 3, "actioned": 2}}) == 0.0
    assert _line_staged_qty({"quantity": {"active": -2}}) == -2.0
