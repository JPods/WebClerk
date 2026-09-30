"""GL rows are addressed by event, and a reversal names the row it reverses (Fable review H1;
GL-by-layer plan step 1, Bill 2026-09-30).

Reversal by position ("the first k originals are the reversed ones") could not tell two events
of one record apart; reversal_of can.
"""
import pytest

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("chart_of_accounts")]


def _invoice():
    from apps.orgs.models import OrgBase
    from apps.transactions.models import Invoice
    buyer = OrgBase.objects.create(company='Buyer', org_type='customer', is_active=True)
    return Invoice.objects.create(customer_id=buyer.pk, finance={'sales_tax_rate': 0})


def _post(record, event_id, amount):
    from apps.accounts.models import GlJournal
    for account, debit, credit in (('1200-inventory', amount, 0), ('1210-work_in_process', 0, amount)):
        GlJournal.objects.create(account=account, debit=debit, credit=credit, source='automation',
                                 source_id=record.pk, source_model=record._meta.model_name,
                                 event_id=event_id)


def _standing(record, event_id):
    from apps.accounts.models import GlJournal
    rows = GlJournal.objects.filter(source_id=record.pk, source_model=record._meta.model_name,
                                    event_id=event_id)
    reversed_ids = set(GlJournal.objects.filter(reversal_of__in=rows.values('id'))
                       .values_list('reversal_of', flat=True))
    return [r for r in rows if r.pk not in reversed_ids]


def test_reversing_one_event_leaves_the_other_standing():
    from apps.accounts.services.ledger_balance import reverse_gl_entries
    record = _invoice()
    _post(record, 'ev-a', 10)
    _post(record, 'ev-b', 25)
    assert reverse_gl_entries(record, event_id='ev-a') == 2
    assert _standing(record, 'ev-a') == []
    assert len(_standing(record, 'ev-b')) == 2


def test_a_reversal_names_its_row_and_is_not_repeated():
    from apps.accounts.models import GlJournal
    from apps.accounts.services.ledger_balance import reverse_gl_entries
    record = _invoice()
    _post(record, 'ev-a', 10)
    reverse_gl_entries(record, event_id='ev-a')
    reversals = GlJournal.objects.filter(source_model='invoice_reversal', source_id=record.pk)
    originals = GlJournal.objects.filter(source_model='invoice', source_id=record.pk)
    assert sorted(reversals.values_list('reversal_of', flat=True)) == sorted(originals.values_list('id', flat=True))
    assert all(r.event_id == 'ev-a' for r in reversals)
    assert reverse_gl_entries(record, event_id='ev-a') == 0


def test_post_reverse_post_reverse_reverses_only_the_new_rows():
    from apps.accounts.services.ledger_balance import reverse_gl_entries
    record = _invoice()
    _post(record, '', 10)
    assert reverse_gl_entries(record) == 2
    _post(record, '', 12)
    assert reverse_gl_entries(record) == 2
    assert reverse_gl_entries(record) == 0


def test_the_new_roles_resolve_to_the_chart(chart_of_accounts):
    from apps.accounts.services.chart import role_account
    assert role_account('received_not_billed') == '2050-received_not_billed'
    assert role_account('opening_balance_equity') == '3050-opening_balance_equity'
