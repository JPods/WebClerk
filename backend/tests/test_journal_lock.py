"""dt_journaled is the one journal lock (Bill, 2026-09-28; plan 2026-09-28-journal-lock-and-layer-parent.md).

Ratchets from Fable's review of that plan: the guards read the STORED mark (R12, the mechanism
behind audit C2-01), a GL reversal writes no mark (R8), a clone is never born journalized (R11),
and Cash carries the same mark as every header.
"""
import secrets
from decimal import Decimal

import pytest

pytestmark = pytest.mark.django_db

JOURNALED = 1790000000000
TEST_PASSWORD = secrets.token_urlsafe(16)


def _invoice_with_line():
    from apps.orgs.models import OrgBase
    from apps.transactions.models import Invoice, InvoiceLine
    buyer = OrgBase.objects.create(company='Buyer', org_type='customer', is_active=True)
    invoice = Invoice.objects.create(customer_id=buyer.pk, finance={'sales_tax_rate': 0},
                                     totals={'total': 100})
    line = InvoiceLine.objects.create(invoice=invoice, quantity={'staged': 1, 'active': 1},
                                      price={'unit': 100, 'amount': 100})
    return invoice, line


def _journalize(record):
    type(record).objects.filter(pk=record.pk).update(dt_journaled=JOURNALED)
    record.refresh_from_db()


def test_a_request_clearing_the_mark_does_not_unlock_its_own_save():
    """C2-01: the guard read the instance after assignment, so {is_locked: false} unlocked the save
    that carried it. The guard now reads the stored row."""
    from apps.transactions.models.base_transaction_model import JournalizedLockError
    invoice, _ = _invoice_with_line()
    _journalize(invoice)
    invoice.dt_journaled = 0
    invoice.totals = {**invoice.totals, 'total': 999}
    with pytest.raises(JournalizedLockError):
        invoice.save()


def test_a_line_of_a_journalized_header_stays_locked_whatever_the_header_instance_says():
    from apps.transactions.models.base_line_model import JournalizedLineError
    invoice, line = _invoice_with_line()
    _journalize(invoice)
    line.invoice.dt_journaled = 0          # an in-memory header that claims to be open
    line.price = {'unit': 5, 'amount': 5}
    with pytest.raises(JournalizedLineError):
        line.save()


def test_an_open_invoice_still_saves():
    invoice, line = _invoice_with_line()
    invoice.totals = {**invoice.totals, 'total': 120}
    invoice.save()
    line.price = {'unit': 120, 'amount': 120}
    line.save()


def test_a_gl_reversal_writes_no_mark_on_its_source():
    """R8 / H11: reverse_gl_entries cleared is_locked and left dt_journaled, so invoice 1050-inv
    stood journalized and unlocked. Only the unjournalize command clears the mark."""
    from apps.accounts.services.ledger_balance import reverse_gl_entries
    invoice, _ = _invoice_with_line()
    _journalize(invoice)
    reverse_gl_entries(invoice, reason='test')
    invoice.refresh_from_db()
    assert invoice.dt_journaled == JOURNALED


def test_a_superuser_who_unlocks_the_journal_mark_may_change_it(django_user_model):
    """The sibling of the test above (Bill, 2026-09-29): a superuser names the stamp in
    _unlock and the change goes through."""
    from rest_framework.test import APIClient
    from rest_framework_simplejwt.tokens import RefreshToken
    admin = django_user_model.objects.create_superuser(email='jl-unlock@example.com',
                                                       password=TEST_PASSWORD)
    token = RefreshToken.for_user(admin)
    token['role'] = getattr(admin, 'role', 'admin')
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')
    invoice, _ = _invoice_with_line()
    _journalize(invoice)
    resp = client.put(f'/wcapi/invoice/{invoice.pk}/',
                      {'dt_journaled': 0, 'version': invoice.version, '_unlock': ['dt_journaled']},
                      format='json')
    assert resp.status_code == 200, resp.content
    invoice.refresh_from_db()
    assert not invoice.dt_journaled


def test_a_clone_of_a_journalized_invoice_is_not_journalized():
    """R11 / H5."""
    from apps.core.services.record_clone import clone_record
    from apps.transactions.models import Invoice
    invoice, _ = _invoice_with_line()
    _journalize(invoice)
    result = clone_record('invoice', invoice.pk, include_children=True)
    assert 'error' not in result, result
    assert Invoice.objects.get(pk=result['clone_id']).dt_journaled == 0


def test_journalizing_cash_sets_its_mark_and_the_batch_selects_by_it():
    from apps.accounts.services.journalize import journalize_cash
    from apps.transactions.models import Cash
    cash = Cash.objects.create(amount=Decimal('0.00'), purpose='payment')
    assert cash.dt_journaled == 0
    assert Cash.objects.filter(dt_journaled=0, pk=cash.pk).exists()
    out = journalize_cash(cash.pk)
    assert out['status'] == 'auto_completed', out
    cash.refresh_from_db()
    assert cash.dt_journaled > 0
    assert not Cash.objects.filter(dt_journaled=0, pk=cash.pk).exists()


def test_a_journalized_cash_cannot_be_deleted():
    from apps.transactions.models import Cash
    cash = Cash.objects.create(amount=Decimal('5.00'), purpose='payment')
    _journalize(cash)
    with pytest.raises(Exception):
        cash.delete()
    assert Cash.objects.filter(pk=cash.pk).exists()


def test_a_superuser_put_cannot_clear_the_journal_mark(django_user_model):
    """C2-01 end to end: PUT {"dt_journaled": 0} on a journalized invoice is refused with
    coaching (Bill, 2026-09-28), even for a superuser; the invoice stays journalized."""
    from rest_framework.test import APIClient
    from rest_framework_simplejwt.tokens import RefreshToken
    admin = django_user_model.objects.create_superuser(email='jl-admin@example.com',
                                                       password=TEST_PASSWORD)
    token = RefreshToken.for_user(admin)
    token['role'] = getattr(admin, 'role', 'admin')
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')
    invoice, _ = _invoice_with_line()
    _journalize(invoice)
    resp = client.put(f'/wcapi/invoice/{invoice.pk}/', {'dt_journaled': 0, 'version': invoice.version},
                      format='json')
    assert resp.status_code == 400, resp.content
    assert 'system_field' in resp.content.decode()
    invoice.refresh_from_db()
    assert invoice.dt_journaled == JOURNALED


def test_no_model_setting_or_bundle_names_is_locked():
    """R2: dt_journaled is the one journal lock; is_locked is gone everywhere (Bill, 2026-09-28)."""
    from pathlib import Path
    from django.apps import apps as dj_apps
    from apps.core.models import Setting
    carriers = sorted(m._meta.label for m in dj_apps.get_models()
                      if any(f.name == 'is_locked' for f in m._meta.get_fields()))
    assert not carriers, carriers
    assert not Setting.objects.filter(config__icontains='"is_locked"').exists()
    root = Path(__file__).resolve().parent.parent
    for bundle in ('demo-bundle.json', 'init-bundle.json', 'settings-bundle.json'):
        assert '"is_locked"' not in (root / bundle).read_text(), bundle
