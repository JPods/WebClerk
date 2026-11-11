"""release_journalized_invoices — a one-off data fix (FAULT 20261107T195226; Bill, 2026-11-07).

    manage.py release_journalized_invoices                             # dry run: the rows
    manage.py release_journalized_invoices --apply --backup <pg_dump>  # write, after a backup that exists

Before the release gate (validate_status.JOURNALIZE_FROM, 10e4099) an invoice could be posted to the
GL at planned, open, active or pending, and once posted no status moves — so those invoices were
frozen short of release. Bill's ruling: set them to released, with a comment on each saying why;
the GL entries stand. Written with a queryset update (the journal lock refuses a save), version and
dt_modified bumped. Idempotent: a comment carries a key.
"""
import os
import time

from django.core.management.base import BaseCommand, CommandError
from django.db.models import F

FAULT = 'FAULT 20261107T195226'


def frozen_invoices():
    from apps.transactions.models import Invoice
    from apps.transactions.services.validate_status import JOURNALIZE_FROM
    return (Invoice.objects.filter(dt_journaled__gt=0, is_active=True)
            .exclude(status__in=JOURNALIZE_FROM['invoice']).order_by('pk'))


def release(invoice) -> str:
    """Set ``invoice`` released with the stamped reason; answer the status it had."""
    from apps.core.services.comment_stamp import append_comment
    from apps.transactions.models import Invoice
    old = invoice.status or ''
    append_comment(invoice, 'process',
                   f"Status '{old or 'blank'}' → 'released' by data fix: this invoice was posted to the GL "
                   f"before the release gate existed, and a posted record's status cannot move "
                   f"({FAULT}; Bill, 2026-11-07). The GL entries stand.",
                   source='data_fix', key=f'release-journalized-{invoice.pk}')
    Invoice.objects.filter(pk=invoice.pk).update(
        status='released', comments=invoice.comments,
        version=F('version') + 1, dt_modified=int(time.time() * 1000))
    return old


class Command(BaseCommand):
    help = 'Release the invoices posted to the GL before the release gate (dry run unless --apply --backup <file>).'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='Write the fix.')
        parser.add_argument('--backup', help='The pg_dump taken first; required with --apply.')

    def handle(self, *args, **options):
        rows = list(frozen_invoices())
        self.stdout.write(f'Journalized invoices short of release: {len(rows)}')
        for inv in rows:
            self.stdout.write(f'  {inv.pk:6d}  {inv.ida:<12} status {inv.status!r:<16} journalized {inv.dt_journaled}')
        if not options['apply']:
            self.stdout.write("Dry run — pass --apply --backup <pg_dump file> to set them 'released' with a comment each.")
            return
        backup = options.get('backup')
        if not backup or not os.path.isfile(backup):
            raise CommandError('--apply needs --backup <file>: the pg_dump taken before this data change (Bill: back up first).')
        for inv in rows:
            old = release(inv)
            self.stdout.write(f"  released {inv.ida} (was {old!r})")
        self.stdout.write(self.style.SUCCESS(f'Applied: {len(rows)} invoices released; backup {backup}'))
