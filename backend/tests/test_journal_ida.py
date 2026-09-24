"""A journal line's ida names the document it posts, and fits in 40 characters.

Defect B-2 (2026-09-23): ``SJ-{invoice.ida}-{account}`` overflowed gl_journals.ida
(varchar 40) — a database error, not an answer. The account has its own column; the ida
now carries only ``{prefix}{kind}-{source ida}``, shared by every line of the document,
and a reference that still would not fit is refused by name instead of clipped.
"""
import pytest

from apps.accounts.services.journalize import IDA_MAX, journal_ida
from tests.test_gl_posting import invoice_with_line


def test_the_ida_names_the_document_not_the_account():
    assert journal_ida('', 'SJ', 'INV-1001') == 'SJ-INV-1001'
    assert journal_ida('zz', 'CJ', 'CASH-7') == 'zzCJ-CASH-7', "training prefix stays first"


def test_an_ida_that_cannot_fit_is_refused_by_name_not_clipped():
    long_ida = 'X' * (IDA_MAX - 2)
    with pytest.raises(ValueError) as caught:
        journal_ida('zz', 'SJ', long_ida)
    assert long_ida in str(caught.value) and str(IDA_MAX) in str(caught.value)


@pytest.mark.django_db
@pytest.mark.usefixtures("chart_of_accounts")
def test_an_invoice_with_a_long_ida_posts_every_line_under_one_reference():
    """The shape that overflowed: a 30-character invoice ida plus an account code."""
    from apps.accounts.models import GlJournal
    from apps.accounts.services.journalize import journalize_invoice

    invoice = invoice_with_line(250.0, unit_cost=100.0)
    invoice.ida = 'INV-2026-LONG-REFERENCE-000001'
    invoice.save(update_fields=['ida'])

    result = journalize_invoice(invoice.pk)

    assert result.get('created', 0) >= 2, result
    idas = set(GlJournal.objects.filter(source_id=invoice.pk, source_model='invoice')
               .values_list('ida', flat=True))
    assert idas == {f'SJ-{invoice.ida}'}


@pytest.mark.django_db
@pytest.mark.usefixtures("chart_of_accounts")
def test_a_document_too_long_to_journal_is_an_exception_result_not_a_crash():
    from apps.accounts.models import GlJournal
    from apps.accounts.services.journalize import journalize_invoice

    invoice = invoice_with_line(80.0)
    invoice.ida = 'I' * IDA_MAX
    invoice.save(update_fields=['ida'])

    result = journalize_invoice(invoice.pk)

    assert result['created'] == 0 and result['status'] == 'exception'
    assert invoice.ida in result['error']
    assert not GlJournal.objects.filter(source_id=invoice.pk, source_model='invoice').exists()
