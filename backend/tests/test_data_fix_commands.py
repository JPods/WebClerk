"""The two one-off data fixes of 2026-11-07 (FAULT 20261107T195226): invoices posted before the
release gate are released with a stamped reason; GL rows written before the stamp take their
document's posting moment or their own dt_created. Dry run by default; --apply needs a backup."""
import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.orgs.models import Customer
from apps.transactions.models import Invoice, InvoiceLine

pytestmark = pytest.mark.django_db


def _posted_invoice(status, ida=''):
    buyer = Customer.objects.create(company='Fix Buyer')
    inv = Invoice.objects.create(customer_id=buyer.pk, terms='N30', status=status, finance={'sales_tax_rate': 0},
                                 totals={'total': 10})
    InvoiceLine.objects.create(invoice=inv, quantity={'staged': 1, 'active': 1}, price={'unit': 10, 'amount': 10})
    # posted after its line: a journalized header takes no new line
    Invoice.objects.filter(pk=inv.pk).update(dt_journaled=1700000000000, **({'ida': ida} if ida else {}))
    inv.refresh_from_db()
    return inv


def test_release_journalized_invoices_releases_only_the_frozen_rows_with_a_reason(tmp_path, capsys):
    frozen = _posted_invoice('planned')
    fine = _posted_invoice('released')
    version = frozen.version
    call_command('release_journalized_invoices')
    assert 'Journalized invoices short of release: 1' in capsys.readouterr().out
    frozen.refresh_from_db()
    assert frozen.status == 'planned'                                  # a dry run writes nothing
    with pytest.raises(CommandError):
        call_command('release_journalized_invoices', '--apply')
    backup = tmp_path / 'wc.dump'; backup.write_text('x')
    call_command('release_journalized_invoices', '--apply', '--backup', str(backup))
    frozen.refresh_from_db(); fine.refresh_from_db()
    assert frozen.status == 'released' and frozen.version == version + 1
    assert "'planned' → 'released'" in frozen.comments['process'][-1]['mgs']
    assert fine.status == 'released'
    call_command('release_journalized_invoices', '--apply', '--backup', str(backup))   # idempotent
    frozen.refresh_from_db()
    assert len(frozen.comments['process']) == 1


def test_stamp_gl_rows_takes_the_documents_moment_or_the_rows_own(tmp_path, chart_of_accounts, capsys):
    from apps.accounts.models import GlJournal
    inv = _posted_invoice('released')
    from apps.accounts.models import GlAccount
    account = GlAccount.objects.filter(is_active=True).values_list('ida', flat=True).first()
    doc_row = GlJournal.objects.create(ida='SJ-doc', account=account, debit=10.0, source='automation', type='sales',
                                       source_model='invoice', source_id=inv.pk)
    own_row = GlJournal.objects.create(ida='SJ-own', account=account, credit=10.0, source='automation', type='sales',
                                       source_model='invoice_reversal', source_id=inv.pk)
    GlJournal.objects.filter(pk__in=[doc_row.pk, own_row.pk]).update(dt_journaled=0)   # rows from before the stamp
    call_command('stamp_gl_rows')
    out = capsys.readouterr().out
    assert 'Unstamped GL rows: 2' in out
    backup = tmp_path / 'wc.dump'; backup.write_text('x')
    call_command('stamp_gl_rows', '--apply', '--backup', str(backup))
    doc_row.refresh_from_db(); own_row.refresh_from_db()
    assert doc_row.dt_journaled == inv.dt_journaled == 1700000000000
    assert own_row.dt_journaled == own_row.dt_created > 0
    assert not GlJournal.objects.filter(dt_journaled=0).exists()
