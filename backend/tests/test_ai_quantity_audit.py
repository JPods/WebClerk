"""The quantity check reads the same children sum the line's save used (line._children_sum)."""
from types import SimpleNamespace

from apps.accounts.services import ai_audit


def _line(quantity, children_sum=None):
    line = SimpleNamespace(quantity=quantity, pk=1, parent_id=1, line_number=1, item={},
                           _meta=SimpleNamespace(model_name="quoteline"))
    if children_sum is not None:
        line._children_sum = children_sum
    return line


def test_fully_consumed_parent_line_is_consistent(monkeypatch):
    """A quote line of 19 whose order line took 19 has remaining 0: no discrepancy."""
    monkeypatch.setattr(ai_audit, "WRITE_AUDIT_RECORDS", False)
    q = {"active": 19.0, "staged": 19.0, "remaining": 0.0}
    assert ai_audit.check_quantity(_line(q, children_sum=19.0), dict(q)) == []


def test_line_without_children_keeps_remaining_equal_to_active(monkeypatch):
    monkeypatch.setattr(ai_audit, "WRITE_AUDIT_RECORDS", False)
    q = {"active": 19.0, "staged": 19.0, "remaining": 19.0}
    assert ai_audit.check_quantity(_line(q), dict(q)) == []


def test_wrong_remaining_is_still_reported(monkeypatch):
    """Children took 9 of 19 but remaining says 19: the check must speak."""
    monkeypatch.setattr(ai_audit, "WRITE_AUDIT_RECORDS", False)
    q = {"active": 19.0, "staged": 19.0, "remaining": 19.0}
    found = ai_audit.check_quantity(_line(q, children_sum=9.0), dict(q))
    assert [d["field"] for d in found] == ["quantity.remaining"]
    assert found[0]["calculated"] == 10.0
