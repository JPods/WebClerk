"""
Sync canonical report definitions to the database (idempotent).

Thin wrapper around common.sync_wcreact.reports — all data and logic lives there.

Usage:
    python manage.py sync_reports                    # create/update all reports
    python manage.py sync_reports --dry-run           # preview changes only
    python manage.py sync_reports --list              # show current reports in DB
    python manage.py sync_reports --model customer    # limit to one model
    python manage.py sync_reports --direction to-r25  # output as r25 TypeScript
"""

from django.core.management.base import BaseCommand
from common.sync_wcreact.reports import sync_reports, list_reports, show_reports_for_r25


class Command(BaseCommand):
    help = "Sync canonical report/print definitions to the database (idempotent)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview what would be created/updated without saving",
        )
        parser.add_argument(
            "--list",
            action="store_true",
            help="List current reports in the database and exit",
        )
        parser.add_argument(
            "--direction",
            choices=["to-wc3", "to-r25"],
            default="to-wc3",
            help="to-wc3: sync report defs → DB.  to-r25: output as r25 TypeScript.",
        )
        parser.add_argument(
            "--model",
            action="append",
            dest="models",
            help="Limit to specific model key(s). Can be repeated.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        models = options.get("models")

        if options["list"]:
            list_reports(self.stdout, models=models)
            return

        if options["direction"] == "to-r25":
            show_reports_for_r25(self.stdout, models=models)
            return

        sync_reports(self.stdout, self.style, models=models, dry_run=dry_run)

        if not dry_run:
            self.stdout.write("")
            list_reports(self.stdout, models=models)
