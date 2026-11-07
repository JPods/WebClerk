"""sweep_defaults — existing records get the defaults they were born without (readme 106 step 4).

    manage.py sweep_defaults                               # dry run: counts per model and field
    manage.py sweep_defaults --apply --backup <pg_dump>    # write, after a backup that exists

Blanks are filled from each model's own definition (a dt_ field as born + days); a value off
its list is reported, never rewritten (Alice coaches the owner: watch_defaults); the company
profile's unread prefs.currency keys (code, locale, symbol) are dropped. Training rows are
never touched. Bill: back up before a bulk change — --apply refuses without --backup naming a
file that exists.
"""
import os

from django.core.management.base import BaseCommand, CommandError

from apps.core.services import defaults_sweep


class Command(BaseCommand):
    help = 'Fill the blank defaults of existing records (dry run unless --apply --backup <file>).'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='Write the repairs.')
        parser.add_argument('--backup', help='The pg_dump taken first; required with --apply.')

    def handle(self, *args, **options):
        findings = defaults_sweep.find_all()
        blanks = [f for f in findings if f.kind == 'blank']
        unlisted = [f for f in findings if f.kind == 'unlisted']
        profile = [f for f in findings if f.kind == 'profile']
        self.stdout.write(f'Blank defaults: {sum(f.count for f in blanks)} rows on {len(blanks)} model fields')
        for f in blanks:
            self.stdout.write(f'  {f.count:6d}  {f.model}.{f.field} ← {f.value!r}   ids {f.ids[:8]}{"…" if f.count > 8 else ""}')
        self.stdout.write(f'Off the list (reported, never rewritten): {sum(f.count for f in unlisted)} rows on {len(unlisted)} values')
        for f in unlisted:
            self.stdout.write(f'  {f.count:6d}  {f.model}.{f.field} = {f.value!r}   ids {f.ids[:8]}{"…" if f.count > 8 else ""}')
        for f in profile:
            self.stdout.write(f'Company profile prefs.currency: unread keys {f.value} (dropped on apply; precisions stay)')
        if not options['apply']:
            self.stdout.write('Dry run — pass --apply --backup <pg_dump file> to write.')
            return
        backup = options.get('backup')
        if not backup or not os.path.isfile(backup):
            raise CommandError('--apply needs --backup <file>: the pg_dump taken before this bulk change (Bill: back up first).')
        written = defaults_sweep.apply(findings)
        for key, n in sorted(written.items()):
            self.stdout.write(f'  wrote {n:6d}  {key}')
        self.stdout.write(self.style.SUCCESS(f'Applied: {sum(written.values())} rows; backup {backup}'))
