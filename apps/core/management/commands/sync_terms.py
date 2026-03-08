"""
Sync canonical payment terms to the database (idempotent).

Thin wrapper around common.sync_wcreact.terms — all data and logic lives there.

Usage:
    python manage.py sync_terms              # create/update terms
    python manage.py sync_terms --dry-run    # preview changes only
    python manage.py sync_terms --list       # show current terms in DB
"""

from django.core.management.base import BaseCommand
from common.sync_wcreact.terms import sync_terms, list_terms


class Command(BaseCommand):
    help = "Sync canonical payment terms to the database (idempotent)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview what would be created/updated without saving",
        )
        parser.add_argument(
            "--list",
            action="store_true",
            help="List current terms in the database and exit",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        if options["list"]:
            list_terms(self.stdout)
            return

        sync_terms(self.stdout, self.style, dry_run=dry_run)

        if not dry_run:
            self.stdout.write("")
            list_terms(self.stdout)
