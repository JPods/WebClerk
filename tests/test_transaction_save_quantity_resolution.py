from apps.transactions.services.transaction_save import _line_staged_qty


def test_line_staged_qty_prefers_active_over_staged():
    qty = _line_staged_qty({"quantity": {"staged": 7, "active": 4}})
    assert qty == 4.0


def test_line_staged_qty_supports_legacy_quantity_keys():
    qty = _line_staged_qty({"quantity": {"placed": 3, "actioned": 2}})
    assert qty == 3.0
