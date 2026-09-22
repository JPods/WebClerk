"""One edit, one recomputation.

Saving five lines of an invoice recomputed that invoice five times and saved its header
five times, so one edit bumped the header's version by five (save-path review,
2026-09-22). A document's totals belong to the document, not to each line of it.
"""
import pytest

from apps.core.services import unit_of_work as uow

pytestmark = pytest.mark.django_db


# ── the scope itself ──────────────────────────────────────────────────

def test_work_deferred_inside_a_unit_runs_once_on_the_way_out():
    done = []
    with uow.unit_of_work():
        for _ in range(5):
            assert uow.defer(('invoice', 41), lambda: done.append('recalc')) is True
        assert done == [], "nothing runs while the unit is open"
    assert done == ['recalc'], "five marks, one recomputation"


def test_two_documents_are_two_recomputations():
    done = []
    with uow.unit_of_work():
        uow.defer(('invoice', 41), lambda: done.append(41))
        uow.defer(('invoice', 42), lambda: done.append(42))
        uow.defer(('invoice', 41), lambda: done.append(41))
    assert sorted(done) == [41, 42]


def test_outside_a_unit_nothing_is_deferred():
    """Every caller that has not been converted keeps working exactly as before."""
    assert uow.active() is False
    assert uow.defer(('invoice', 41), lambda: None) is False


def test_units_nest_and_only_the_outermost_flushes():
    done = []
    with uow.unit_of_work():
        uow.defer(('invoice', 41), lambda: done.append('outer'))
        with uow.unit_of_work():
            uow.defer(('invoice', 42), lambda: done.append('inner'))
            assert done == []
        assert done == [], "an inner unit closing does not flush the outer one's work"
    assert sorted(done) == ['inner', 'outer']


def test_a_failure_in_deferred_work_reaches_the_caller():
    """Fail hard: totals that silently failed to recompute are totals nobody can trust."""
    def _boom():
        raise RuntimeError('recompute failed')

    with pytest.raises(RuntimeError, match='recompute failed'):
        with uow.unit_of_work():
            uow.defer(('invoice', 41), _boom)


# ── what it is for: a document with lines ─────────────────────────────

def _invoice_with_lines(line_count: int):
    from apps.orgs.models import OrgBase
    from apps.products.models import Item
    from apps.transactions.models import Invoice, InvoiceLine

    customer = OrgBase.objects.create(company='UoW Customer', org_type='customer',
                                      is_active=True)
    item = Item.objects.create(name='UoW Widget', ida='zz-uow-item')
    invoice = Invoice.objects.create(customer_id=customer.pk, status='open')
    return invoice, item, InvoiceLine


def test_a_document_saved_with_its_lines_recomputes_once(monkeypatch):
    """Bill, 2026-09-22: lines are an object on the document, applied to their lines by
    id. So the unit is the document — header and lines together — and the totals engine
    is asked once for the whole of it, not once per line.

    Counted at the engine, which is what this change moves. The header is still written
    more than once per edit for reasons a layer down (each recompute writes it again
    through ledger_balance; the door writes it again for keywords and org links). Those
    are measured in the save-path review and are not this.
    """
    from apps.core.services.door import Actor
    from apps.core.services.save import save_record
    from apps.transactions.services.pricing import totals_compute

    calls = []
    original = totals_compute.recalculate_totals

    def counting(pk, model_name, *a, **k):
        calls.append((model_name, pk))
        return original(pk, model_name, *a, **k)

    monkeypatch.setattr(totals_compute, 'recalculate_totals', counting)

    invoice, item, _lines = _invoice_with_lines(3)
    invoice.refresh_from_db()

    save_record(Actor.system(), {
        'model_name': 'invoice',
        'id': invoice.pk,
        'version': invoice.version,
        'lines': [
            {'line_number': (n + 1) * 10, 'item_fk': item.pk,
             'item': {'name': item.name, 'ida': item.ida},
             'quantity': {'active': 1}, 'price': {'unit': 10.0}}
            for n in range(3)
        ],
    })

    for_this_invoice = [c for c in calls if c == ('invoice', invoice.pk)]
    assert len(for_this_invoice) == 1, (
        f"three lines in one document edit asked the totals engine "
        f"{len(for_this_invoice)} times; it is one document, so it is one answer")

    invoice.refresh_from_db()
    assert float((invoice.totals or {}).get('total') or 0) == 30.0, "and it is right"


def test_without_a_unit_the_old_behaviour_is_unchanged():
    """The per-line recompute still happens for any caller not yet converted — which is
    why this could land without touching them."""
    invoice, item, InvoiceLine = _invoice_with_lines(2)
    invoice.refresh_from_db()
    before = invoice.version

    for n in range(2):
        InvoiceLine.objects.create(
            invoice_id=invoice.pk, line_number=(n + 1) * 10, item_fk=item,
            item={'name': item.name, 'ida': item.ida},
            quantity={'active': 1}, price={'unit': 10.0})

    invoice.refresh_from_db()
    assert invoice.version > before
    assert float((invoice.totals or {}).get('total') or 0) == 20.0
