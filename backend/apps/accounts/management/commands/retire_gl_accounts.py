"""retire_gl_accounts — move references off accounts the chart replaced, then remove them.

Usage:
    python manage.py retire_gl_accounts            # show what would move
    python manage.py retire_gl_accounts --apply    # move references, delete the old accounts

The replacements are seed_gl_accounts.REPLACED (old code → new code). Run
seed_gl_accounts first so every new code exists. An old account is deleted only when
nothing names it any more.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.management.commands.seed_gl_accounts import REPLACED
from apps.accounts.models.gl_account import GlAccount
from apps.accounts.services.chart import move_account_references


class Command(BaseCommand):
    help = 'Move references off replaced GL accounts and delete them'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='Make the changes (default: report only)')

    def handle(self, *args, **options):
        apply = options['apply']
        with transaction.atomic():
            for old, new in REPLACED.items():
                if not GlAccount.objects.filter(ida=old).exists():
                    continue
                moved = move_account_references(old, new)
                GlAccount.objects.filter(ida=old).delete()
                self.stdout.write(f'{old} → {new}: {moved or "no references"}')
            if not apply:
                transaction.set_rollback(True)
                self.stdout.write(self.style.WARNING('Report only — run with --apply to make these changes.'))
