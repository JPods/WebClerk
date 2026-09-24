"""An effect of a status change is keyed on the transition and runs after the commit
(plan 2026-09-24 §11.6c). Shipping saves an invoice three times; the customer gets one
email. A save that rolls back tells no one.
"""
import pytest
from django.db import transaction

from apps.transactions.models import Cash, Invoice
from apps.transactions.services import notify_email

pytestmark = pytest.mark.django_db


@pytest.fixture
def sent(monkeypatch):
    calls = []
    service = notify_email.TransactionEmailService
    for name in ('send_invoice_sent_notification', 'send_cash_received_notification'):
        monkeypatch.setattr(service, name,
                            staticmethod(lambda obj, _n=name: calls.append((_n, obj.pk))))
    return calls


def test_an_invoice_released_and_saved_again_sends_one_email(
        sent, django_capture_on_commit_callbacks):
    invoice = Invoice.objects.create(status='open')
    with django_capture_on_commit_callbacks(execute=True):
        invoice.status = Invoice.STATUS_RELEASED
        invoice.save()
        invoice.metadata = {**(invoice.metadata or {}), 'shipped': True}
        invoice.save(update_fields=['metadata'])
        invoice.save()
    assert sent == [('send_invoice_sent_notification', invoice.pk)]


def test_a_rolled_back_release_sends_nothing(sent, django_capture_on_commit_callbacks):
    invoice = Invoice.objects.create(status='open')
    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        try:
            with transaction.atomic():
                invoice.status = Invoice.STATUS_RELEASED
                invoice.save()
                raise RuntimeError('the ship failed')
        except RuntimeError:
            pass
    assert sent == [] and callbacks == []


def test_a_completed_cash_sends_one_received_email(sent, django_capture_on_commit_callbacks):
    cash = Cash.objects.create(amount=10, status='processing', method='card')
    with django_capture_on_commit_callbacks(execute=True):
        cash.status = 'completed'
        cash.add_audit_entry('gateway_completed', {})
        cash.save()
        cash.save(update_fields=['metadata'])
    assert sent == [('send_cash_received_notification', cash.pk)]
