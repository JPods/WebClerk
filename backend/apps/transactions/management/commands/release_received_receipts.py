"""Release the receipts that received goods before receiving released them (Bill, 2026-11-26).

Since readme 108 (2026-11-11) saving a receipt receives its goods, but convert left every receipt
'planned' and a payment rewrote the status to open/partially_paid/paid. Bill ruled "Released when
received": a receipt that has received reads 'released', its paid state is its totals. Receipts
made before that ruling are moved here, once, through the save door as our own code (its hooks
and history run, as for any save). A status a person set (approved, on_hold, ...) stays.

    manage.py release_received_receipts            # lists what it would move
    manage.py release_received_receipts --apply    # moves them
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Release receipts that have received goods but still read planned or blank."

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='Move them; without it, only list.')

    def handle(self, *args, **opts):
        from apps.core.services.door import Actor
        from apps.core.services.save import save_record
        from apps.transactions.behaviours import awaits_release
        from apps.transactions.models import Receipt

        waiting = [r for r in Receipt.objects.order_by('pk') if awaits_release(r)]
        for receipt in waiting:
            self.stdout.write(f"receipt {receipt.ida or receipt.pk} (#{receipt.pk}): "
                              f"'{receipt.status}' -> 'released'")
        if not opts['apply']:
            self.stdout.write(f"{len(waiting)} to release. Run with --apply to move them.")
            return
        actor = Actor.system(source='release_received_receipts')
        for receipt in waiting:
            save_record(actor, {'id': receipt.pk, 'version': receipt.version, 'status': 'released'},
                        model_key='receipt')
        self.stdout.write(self.style.SUCCESS(f"{len(waiting)} released."))
