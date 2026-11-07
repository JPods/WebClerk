"""stamp_gl_rows — a one-off data fix (the lead, 2026-11-07, with FAULT 20261107T195226).

    manage.py stamp_gl_rows                             # dry run: counts per source
    manage.py stamp_gl_rows --apply --backup <pg_dump>  # write, after a backup that exists

GlJournal.save now stamps dt_journaled when a row is written (10e4099's successor), but every row
written before carries 0, and the dashboard counts dt_journaled=0 as unposted (dashboard_pending) —
so every posting ever made showed as unposted. The backfill: a row whose source document
(invoice, cash, receipt, workorder) carries dt_journaled takes that moment; any other row (a
reversal, an adjustment, a purchase posting from before purchases stopped posting) takes its own
dt_created. Nothing else on the row changes.
"""
import os
from collections import Counter

from django.core.management.base import BaseCommand, CommandError
from django.db.models import F

DOCUMENTS = {'invoice': ('transactions', 'Invoice'), 'cash': ('transactions', 'Cash'),
             'receipt': ('transactions', 'Receipt'), 'workorder': ('transactions', 'WorkOrder')}


def plan():
    """[(row, stamp, origin)] for every unstamped GL row: stamp is the ms to write; origin is
    'document' when the source document gave it, 'row' when the row's own dt_created did."""
    from django.apps import apps as dj_apps
    from apps.accounts.models import GlJournal
    rows = list(GlJournal.objects.filter(dt_journaled=0).order_by('pk'))
    by_model = {}
    for row in rows:
        if row.source_model in DOCUMENTS:
            by_model.setdefault(row.source_model, set()).add(row.source_id)
    moments = {}
    for model_key, ids in by_model.items():
        Model = dj_apps.get_model(*DOCUMENTS[model_key])
        for pk, dt in Model.objects.filter(pk__in=ids, dt_journaled__gt=0).values_list('pk', 'dt_journaled'):
            moments[(model_key, pk)] = dt
    out = []
    for row in rows:
        dt = moments.get((row.source_model, row.source_id))
        if dt:
            out.append((row, dt, 'document'))
        else:
            out.append((row, row.dt_created, 'row'))
    return out


def apply(planned) -> int:
    from apps.accounts.models import GlJournal
    written = 0
    for row, stamp, _origin in planned:
        written += GlJournal.objects.filter(pk=row.pk, dt_journaled=0).update(dt_journaled=stamp or F('dt_created'))
    return written


class Command(BaseCommand):
    help = 'Stamp dt_journaled on the GL rows written before the stamp existed (dry run unless --apply --backup <file>).'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='Write the stamps.')
        parser.add_argument('--backup', help='The pg_dump taken first; required with --apply.')

    def handle(self, *args, **options):
        planned = plan()
        counts = Counter((row.source_model, origin) for row, _stamp, origin in planned)
        self.stdout.write(f'Unstamped GL rows: {len(planned)}')
        for (source_model, origin), n in sorted(counts.items()):
            self.stdout.write(f'  {n:6d}  {source_model:<18} ← {"the source document's dt_journaled" if origin == "document" else "the row's own dt_created"}')
        if not options['apply']:
            self.stdout.write('Dry run — pass --apply --backup <pg_dump file> to write.')
            return
        backup = options.get('backup')
        if not backup or not os.path.isfile(backup):
            raise CommandError('--apply needs --backup <file>: the pg_dump taken before this data change (Bill: back up first).')
        written = apply(planned)
        self.stdout.write(self.style.SUCCESS(f'Applied: {written} GL rows stamped; backup {backup}'))
