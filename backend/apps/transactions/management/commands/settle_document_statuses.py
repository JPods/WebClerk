"""Set invoice and receipt statuses from their facts, once (Bill, 2026-11-27: "I have not been paying
attention to status in the invoices and receipts I processed. So mark them as makes sense.").

From then on the system keeps them (totals_compute.settle_paid_status, behaviours.release_when_received);
the person may set any status. Here, through the save door as our own code:

    fully paid (its figure, recomputed)          -> paid
    shipped (an invoice with lines) or received
    (a receipt line received) and not fully paid -> released   (also a 'paid' whose figure is partial)
    no lines, nothing received, canceled, void   -> left as it is
    a release the gate would refuse (no terms...) -> left, and listed with what it lacks

    manage.py settle_document_statuses            # lists what it would change
    manage.py settle_document_statuses --apply    # changes them
"""
from decimal import Decimal

from django.core.management.base import BaseCommand

LEFT_ALONE = ('canceled', 'void', 'voided')


def status_from_facts(doc, model_key: str):
    """The status its facts say, or None to leave it (and why)."""
    from apps.transactions.models import InvoiceLine, ReceiptLine
    from apps.transactions.services.cash.cash_pending import cash_state
    if (doc.status or '') in LEFT_ALONE:
        return None, (doc.status or '')
    totals = doc.totals if isinstance(doc.totals, dict) else {}
    settled = Decimal(str(totals.get('received' if model_key == 'invoice' else 'paid') or 0))
    figure = cash_state(Decimal(str(totals.get('total') or 0)), settled + Decimal(str(totals.get('adjusted') or 0)))
    if model_key == 'invoice':
        if not InvoiceLine.objects.filter(invoice_id=doc.pk).exists():
            return None, 'no lines'
    else:
        quantities = ReceiptLine.objects.filter(receipt_id=doc.pk).values_list('quantity', flat=True)
        if not any(float((q or {}).get('active') or 0) != 0 for q in quantities):
            return None, 'nothing received'
    return ('paid' if figure == 'paid' else 'released'), figure


class Command(BaseCommand):
    help = "Set invoice and receipt statuses from their facts (paid / released)."

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='Change them; without it, only list.')

    def handle(self, *args, **opts):
        from apps.core.services.door import Actor, Refused
        from apps.core.services.save import save_record
        from apps.transactions.models import Invoice, Receipt
        from apps.transactions.services import validate_status

        moves = []
        for model_key, Model in (('invoice', Invoice), ('receipt', Receipt)):
            for doc in Model.objects.filter(is_active=True).order_by('pk'):
                target, why = status_from_facts(doc, model_key)
                if target is None or target == (doc.status or ''):
                    continue
                journalized = ' (journalized)' if getattr(doc, 'dt_journaled', 0) else ''
                name = f"{model_key} {doc.ida or doc.pk} (#{doc.pk})"
                missing = validate_status.incomplete(doc, model_key) if target == 'released' else []
                if missing:      # the release gate would refuse it: say so, leave it
                    self.stdout.write(f"{name}: left '{doc.status or ''}', cannot release: lacks "
                                      f"{', '.join(missing)}  [figure {why}]{journalized}")
                    continue
                moves.append((model_key, doc, target))
                self.stdout.write(f"{name}: '{doc.status or ''}' -> '{target}'  [figure {why}]{journalized}")
        if not opts['apply']:
            self.stdout.write(f"{len(moves)} to change. Run with --apply to change them.")
            return
        from apps.transactions.services.status_moves import system_status_move
        actor = Actor.system(source='settle_document_statuses')
        changed = 0
        for model_key, doc, target in moves:
            try:
                with system_status_move():      # a data fix: no "invoice sent" email, no fulfillment event
                    save_record(actor, {'id': doc.pk, 'version': doc.version, 'status': target},
                                model_key=model_key)
                changed += 1
            except Refused as refused:      # one row's refusal never stops the rest
                self.stdout.write(f"{model_key} #{doc.pk}: refused {refused.code}: {refused.message}")
        self.stdout.write(self.style.SUCCESS(f"{changed} of {len(moves)} changed."))
